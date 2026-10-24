export function GET() {
  return Response.json({
    models: [
  {
    "name": "gpt-5.5",
    "model": "openai/gpt-5.5",
    "display_name": "gpt-5.5",
    "supports_thinking": true,
    "supports_vision": true
  },
  {
    "name": "claude-opus-4.7",
    "model": "anthropic/claude-opus-4.7",
    "display_name": "claude-opus-4.7",
    "supports_thinking": true,
    "supports_vision": true
  },
  {
    "name": "deepseek-v3.2",
    "model": "deepseek/deepseek-v3.2",
    "display_name": "deepseek-v3.2",
    "supports_thinking": true,
    "supports_vision": false
  },
  {
    "name": "gemini-3.1",
    "model": "google/gemini-3.1-pro-preview",
    "display_name": "gemini-3.1",
    "supports_thinking": true,
    "supports_vision": true
  },
  {
    "name": "qwen3.6-plus",
    "model": "qwen/qwen3.6-plus",
    "display_name": "qwen3.6-plus",
    "supports_thinking": true,
    "supports_vision": true
  },
  {
    "name": "glm-5.1",
    "model": "z-ai/glm-5.1",
    "display_name": "glm-5.1",
    "supports_thinking": true,
    "supports_vision": false
  },
  {
    "name": "kimi-k2.6",
    "model": "moonshotai/kimi-k2.6",
    "display_name": "kimi-k2.6",
    "supports_thinking": true,
    "supports_vision": true
  },
  {
    "name": "minimax-m2.7",
    "model": "minimax/minimax-m2.7",
    "display_name": "minimax-m2.7",
    "supports_thinking": true,
    "supports_vision": false
  },
  {
    "name": "grok-4.20",
    "model": "x-ai/grok-4.20",
    "display_name": "grok-4.20",
    "supports_thinking": true,
    "supports_vision": true
  },
  {
    "name": "mimo-v2.5-pro",
    "model": "xiaomi/mimo-v2.5-pro",
    "display_name": "mimo-v2.5-pro",
    "supports_thinking": true,
    "supports_vision": false
  },
  {
    "name": "hy3-preview",
    "model": "tencent/hy3-preview",
    "display_name": "hy3-preview",
    "supports_thinking": true,
    "supports_vision": false
  }
]
  });
}
