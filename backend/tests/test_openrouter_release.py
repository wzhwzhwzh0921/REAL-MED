"""Offline transport and benchmark-contract coverage for the public release."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
import yaml
from langchain_core.messages import HumanMessage, ToolMessage

from deerflow.config.app_config import AppConfig
from deerflow.models.openrouter import ChatOpenRouter

ROOT = Path(__file__).resolve().parents[2]


def load_script(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tool_turn_replays_signed_reasoning_and_uses_bearer_auth():
    requests = []
    details = [{"type": "reasoning.encrypted", "data": "opaque-signature", "id": "r1", "index": 0}]

    def handle(request):
        body = json.loads(request.content)
        requests.append((request, body))
        message = {"role": "assistant", "content": "Done"}
        if len(requests) == 1:
            message.update(
                content=None,
                reasoning_details=details,
                tool_calls=[
                    {
                        "id": "call1",
                        "type": "function",
                        "function": {"name": "calculate", "arguments": '{"x":2}'},
                    }
                ],
            )
        return httpx.Response(
            200,
            json={
                "id": "response1",
                "object": "chat.completion",
                "created": 1,
                "model": "moonshotai/kimi-k2.6",
                "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    model = ChatOpenRouter(api_key="offline-test", model="moonshotai/kimi-k2.6", http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    bound = model.bind_tools([{"name": "calculate", "description": "Compute x", "parameters": {"type": "object", "properties": {"x": {"type": "integer"}}}}])
    user = HumanMessage(content="Calculate 2")
    answer = bound.invoke([user], reasoning_effort="high")
    assert answer.tool_calls[0]["args"] == {"x": 2}
    bound.invoke([user, answer, ToolMessage(content="2", tool_call_id="call1")], reasoning_effort="medium")
    request, body = requests[-1]
    assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer offline-test"
    assert "offline-test" not in str(request.url)
    assert body["messages"][1]["reasoning_details"] == details
    assert body["reasoning"]["effort"] == "medium"
    assert "reasoning_effort" not in body
    assert body["tools"][0]["function"]["name"] == "calculate"


@pytest.mark.parametrize("async_mode", [False, True])
def test_streamed_reasoning_signature_survives_chunk_aggregation(async_mode):
    expected = {"type": "reasoning.encrypted", "index": 0, "data": "opaque-signature", "format": "openai-responses-v1"}

    def handle(request):
        events = []
        for text in ["opaque-", "signature"]:
            chunk = {"id": "response1", "object": "chat.completion.chunk", "created": 1, "model": "test", "choices": [{"index": 0, "delta": {"role": "assistant", "reasoning_details": [{**expected, "data": text}]}}]}
            events.append("data: " + json.dumps(chunk) + "\n\n")
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, text="".join(events) + "data: [DONE]\n\n")

    model = ChatOpenRouter(api_key="offline-test", model="test", http_client=httpx.Client(transport=httpx.MockTransport(handle)), http_async_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)))
    if async_mode:
        import asyncio

        async def collect():
            return [chunk async for chunk in model.astream([HumanMessage(content="test")])]

        chunks = asyncio.run(collect())
    else:
        chunks = list(model.stream([HumanMessage(content="test")]))
    combined = chunks[0]
    for chunk in chunks[1:]:
        combined += chunk
    assert combined.additional_kwargs["reasoning_details"] == [expected]
    payload = model._get_request_payload([HumanMessage(content="test"), combined])
    assert payload["messages"][1]["reasoning_details"] == [expected]


def reference_config(monkeypatch):
    raw = yaml.safe_load((ROOT / "config.example.yaml").read_text())
    for name in ["OPENROUTER_API_KEY", "OPENROUTER_API_BASE", "VISION_MODEL", "OPENROUTER_IMAGE_MODEL", "SERPER_API_KEY", "JINA_API_KEY", "SANDBOX_PROVISIONER_URL"]:
        monkeypatch.setenv(name, "offline-test")
    monkeypatch.setenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
    return AppConfig.model_validate(AppConfig.resolve_env_variables(raw))


def test_every_candidate_and_judge_constructs_from_the_example(monkeypatch):
    from deerflow.models import factory

    config = reference_config(monkeypatch)
    monkeypatch.setattr(factory, "get_app_config", lambda: config)
    experiment = yaml.safe_load((ROOT / "evals/experiments/exp_realmed_405case_11model.yaml").read_text())
    for entry in experiment["models"]:
        model = factory.create_chat_model(entry["name"], thinking_enabled=True, reasoning_effort="high")
        payload = model._get_request_payload([HumanMessage(content="test")])
        assert "context_window" not in payload
        assert payload["extra_body"]["reasoning"]["effort"] == "high"
        assert model.openai_api_base == "https://openrouter.ai/api/v1"
    judge = factory.create_chat_model("gpt-5.4-mini", thinking_enabled=False, reasoning_effort="medium")
    assert judge._get_request_payload([HumanMessage(content="judge")])["extra_body"]["reasoning"]["effort"] == "medium"


@pytest.mark.parametrize("name,trigger", [("deepseek-v3.2", 98304), ("gpt-5.5", 525000), ("glm-5.1", 101000)])
def test_paper_context_threshold_and_retention(monkeypatch, name, trigger):
    from deerflow.agents.lead_agent import agent
    from deerflow.config.summarization_config import SummarizationConfig

    config = reference_config(monkeypatch)
    monkeypatch.setattr(agent, "get_app_config", lambda: config)
    monkeypatch.setattr(agent, "get_summarization_config", lambda: SummarizationConfig(enabled=True, trigger={"type": "tokens", "value": 98304}, keep={"type": "tokens", "value": 32768}, trim_tokens_to_summarize=None))
    create = Mock(return_value="resolved-model")
    monkeypatch.setattr(agent, "create_chat_model", create)
    middleware = Mock()
    monkeypatch.setattr(agent, "SummarizationMiddleware", middleware)
    agent._create_summarization_middleware(name)
    assert middleware.call_args.kwargs["trigger"] == ("tokens", trigger)
    assert middleware.call_args.kwargs["keep"] == ("tokens", 32768)
    assert middleware.call_args.kwargs["trim_tokens_to_summarize"] is None
    create.assert_called_once_with(name, thinking_enabled=False)


def test_both_judge_calls_forward_reasoning_effort(tmp_path):
    judge = load_script("release_judge", "scripts/run_judge_eval.py")
    client = Mock()
    client.invoke.return_value = SimpleNamespace(content='{"score":1}')
    judge._call_judge(client, "criterion", "gpt-5.4-mini", reasoning_effort="medium")
    assert client.invoke.call_args.kwargs == {"reasoning_effort": "medium"}
    image = tmp_path / "page.png"
    image.write_bytes(b"offline-image")
    judge._call_vision_judge(client, "visual criterion", [image], "gpt-5.4-mini", reasoning_effort="medium")
    assert client.invoke.call_args.kwargs == {"reasoning_effort": "medium"}
    assert client.invoke.call_args.args[0][0].content[1]["type"] == "image_url"


def test_kubernetes_receives_skill_environment(monkeypatch):
    from deerflow.community.aio_sandbox.remote_backend import RemoteSandboxBackend

    reply = Mock()
    reply.json.return_value = {"sandbox_url": "http://sandbox:8080"}
    post = Mock(return_value=reply)
    monkeypatch.setattr("deerflow.community.aio_sandbox.remote_backend.requests.post", post)
    backend = RemoteSandboxBackend("http://provisioner:8002", {"OPENROUTER_API_KEY": "offline-test"})
    backend.create("thread1", "sandbox1")
    module = load_script("release_provisioner", "docker/provisioner/app.py")
    request = module.CreateSandboxRequest(**post.call_args.kwargs["json"])
    assert "offline-test" not in repr(request)
    pod = module._build_pod(request.sandbox_id, request.thread_id, request.environment)
    env = {entry.name: entry.value for entry in pod.spec.containers[0].env}
    assert env["OPENROUTER_API_KEY"] == "offline-test"
    assert pod.spec.containers[0].image.startswith("ghcr.io/agent-infra/sandbox")


def test_aggregation_includes_visual_points_and_zero_score_runs(tmp_path):
    aggregate = load_script("release_aggregate", "scripts/aggregate_eval.py")
    for name, data in {"run.json": {"model_name": "test", "case": {}}, "summary.json": {"status": "error"}, "judge/score.json": {"total_score": 1, "max_score": 2}, "judge/score_image.json": {"total_score": 2, "max_score": 3}}.items():
        path = tmp_path / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(data))
    data = aggregate.collect_run_data(tmp_path)
    assert data["overall_score"] == 60
    zero = {**data, "overall_score": 0, "total_score": 0, "max_score": 1}
    leaderboard = aggregate.build_leaderboard([data, zero])
    assert leaderboard[0]["avg_score"] == 50
    assert leaderboard[0]["scored_count"] == 2


def test_registry_exposes_the_same_working_skill_and_tool_set_for_every_task(monkeypatch):
    import deerflow.tools.tools as tools_module
    from deerflow.models import factory
    from deerflow.skills.loader import load_skills
    from deerflow.tools.tools import get_available_tools

    config = reference_config(monkeypatch)
    monkeypatch.setattr(factory, "get_app_config", lambda: config)
    monkeypatch.setattr(tools_module, "get_app_config", lambda: config)
    available_tools = {tool.name for tool in get_available_tools(include_mcp=False)}
    assert {"bash", "ls", "read_file", "write_file", "str_replace", "present_files"} <= available_tools
    expected = {"code", "web-search", "web-search-mm", "pdf", "docx", "xlsx", "pptx", "pptx-design", "nano-banana-pro", "draw-io-diagram-generator"}
    for task in (ROOT / "evals/registry/task_types").glob("*.yaml"):
        settings = yaml.safe_load(task.read_text())
        assert set(settings["skills"]) == expected
        extensions = ROOT / "evals/registry" / settings["extensions_config"]
        monkeypatch.setenv("DEER_FLOW_EXTENSIONS_CONFIG_PATH", str(extensions))
        enabled = load_skills(skills_path=ROOT / "skills", use_config=False, enabled_only=True)
        assert {skill.name for skill in enabled} == expected
        assert len(enabled) == len(expected)


def test_image_skills_save_standard_openrouter_images(monkeypatch, tmp_path):
    import base64
    import sys
    from io import BytesIO

    import openai
    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (1, 1), "white").save(buffer, "PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    create = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None, images=[{"image_url": {"url": "data:image/png;base64," + encoded}}]))]))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: client)
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-test")
    nano = load_script("release_nano", "skills/custom/nano-banana-pro/scripts/generate_image.py")
    output = tmp_path / "nano.png"
    monkeypatch.setattr(sys, "argv", ["generate_image.py", "--prompt", "medical diagram", "--filename", str(output)])
    nano.main()
    assert Image.open(output).size == (1, 1)
    assert create.call_args.kwargs["model"] == "google/gemini-3-pro-image"
    assert create.call_args.kwargs["extra_body"]["modalities"] == ["image", "text"]
    public = load_script("release_public_image", "skills/public/image-generation/scripts/generate.py")
    prompt = tmp_path / "prompt.json"
    prompt.write_text('{"description":"medical diagram"}')
    output = tmp_path / "public.png"
    result = public.generate_image(str(prompt), [], str(output))
    assert result.startswith("Successfully generated")
    assert Image.open(output).size == (1, 1)


def test_missing_required_inventory_spreadsheet_is_zero_without_judge_calls(monkeypatch, tmp_path):
    judge = load_script("release_missing_delivery", "scripts/run_judge_eval.py")
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "report.docx").write_bytes(b"document")
    (tmp_path / "run.json").write_text(json.dumps({"model_name": "test", "case": {"case_id": "pharmacy_inventory_management/test"}, "expected_outputs": [{"pattern": "*.docx", "required": True}, {"pattern": "*.xlsx", "required": True}]}))
    summary = {"status": "ok", "output_files": ["report.docx"], "presented_output_files": ["report.docx"]}
    (tmp_path / "summary.json").write_text(json.dumps(summary))
    monkeypatch.setattr(judge, "lookup_rubric", lambda case_id: {"rubrics": ["Medical fact", "Layout requirement"]})
    monkeypatch.setattr(judge, "lookup_image_rubric", lambda case_id: None)
    client = Mock(side_effect=AssertionError("Missing delivery must not call a judge"))
    monkeypatch.setattr(judge, "_make_openai_client", client)
    result = judge.judge_run(tmp_path, {"judge_model": "gpt-5.4-mini"})
    assert result["total_score"] == 0 and result["max_score"] == 2
    assert result["_meta"]["missing_required_outputs"] == ["*.xlsx"]
    client.assert_not_called()
    assert json.loads((tmp_path / "judge/score_image.json").read_text())["max_score"] == 0


def test_file_creation_alone_does_not_count_as_submission(tmp_path):
    judge = load_script("release_submission_contract", "scripts/run_judge_eval.py")
    (tmp_path / "report.pdf").write_bytes(b"%PDF-offline")
    spec = {"expected_outputs": [{"pattern": "*.pdf", "required": True}]}
    summary = {"output_files": ["report.pdf"], "presented_output_files": []}
    assert judge._missing_deliverables(spec, summary, tmp_path) == ["*.pdf"]
    summary["presented_output_files"] = ["report.pdf"]
    assert judge._missing_deliverables(spec, summary, tmp_path) == []
    (tmp_path / "his_result.jsonl").write_text('{"records":{}}')
    assert judge._missing_deliverables({"expected_outputs": [{"pattern": "his_result.jsonl"}]}, {"output_files": ["his_result.jsonl"], "presented_output_files": []}, tmp_path) == []


def test_text_only_candidate_uses_the_configured_openrouter_vision_helper(monkeypatch):
    from deerflow.agents.middlewares.view_image_middleware import ViewImageMiddleware

    config = reference_config(monkeypatch)
    monkeypatch.setattr("deerflow.config.get_app_config", lambda: config)
    middleware = ViewImageMiddleware(model_name="mimo-v2.5-pro")
    assert middleware._supports_vision is False
    assert middleware._proxy_model_name == "gpt-5.4-mini"
