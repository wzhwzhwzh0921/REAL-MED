import os
import shutil
import subprocess

from deerflow.sandbox.local.list_dir import list_dir
from deerflow.sandbox.sandbox import Sandbox


class LocalSandbox(Sandbox):
    _env_cache: dict[str, str] | None = None

    def __init__(self, id: str):
        """
        Initialize local sandbox.

        Args:
            id: Sandbox identifier
        """
        super().__init__(id)

    @staticmethod
    def _get_shell() -> str:
        """Detect available shell executable with fallback.

        Returns the first available shell in order of preference:
        /bin/zsh → /bin/bash → /bin/sh → first `sh` found on PATH.
        Raises a RuntimeError if no suitable shell is found.
        """
        for shell in ("/bin/zsh", "/bin/bash", "/bin/sh"):
            if os.path.isfile(shell) and os.access(shell, os.X_OK):
                return shell
        shell_from_path = shutil.which("sh")
        if shell_from_path is not None:
            return shell_from_path
        raise RuntimeError("No suitable shell executable found. Tried /bin/zsh, /bin/bash, /bin/sh, and `sh` on PATH.")

    @staticmethod
    def _discover_skills_pythonpath() -> str:
        """Discover all skill script directories and build a PYTHONPATH string.

        Scans skills/{public,custom}/<skill>/scripts/ and returns a
        colon-separated path string containing both skill root dirs
        (for ``from scripts.x import y``) and scripts subdirs
        (for ``import x`` directly).
        """
        try:
            from deerflow.config import get_app_config

            skills_root = get_app_config().skills.get_skills_path()
        except Exception:
            return ""

        if not skills_root.exists():
            return ""

        paths: list[str] = []
        try:
            for category_dir in sorted(skills_root.iterdir()):
                if not category_dir.is_dir() or category_dir.name.startswith("."):
                    continue
                for skill_dir in sorted(category_dir.iterdir()):
                    if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                        continue
                    scripts_dir = skill_dir / "scripts"
                    if scripts_dir.is_dir():
                        paths.append(str(skill_dir))
                        paths.append(str(scripts_dir))
        except OSError:
            return ""

        return ":".join(paths)

    def _build_env(self) -> dict[str, str]:
        """Build subprocess environment with skills PYTHONPATH.

        Lazily discovers skill script directories on first call and caches
        the result. Every subprocess executed by this sandbox inherits the
        augmented environment so that models can import skill modules without
        manual ``sys.path.insert`` calls.
        """
        if self._env_cache is not None:
            return self._env_cache

        env = dict(os.environ)

        skills_pypath = self._discover_skills_pythonpath()
        if skills_pypath:
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{skills_pypath}:{existing}" if existing else skills_pypath

        self._env_cache = env
        return env

    def execute_command(self, command: str) -> str:
        result = subprocess.run(
            command,
            executable=self._get_shell(),
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,
            env=self._build_env(),
        )
        output = result.stdout
        if result.stderr:
            output += f"\nStd Error:\n{result.stderr}" if output else result.stderr
        if result.returncode != 0:
            output += f"\nExit Code: {result.returncode}"

        return output if output else "(no output)"

    def list_dir(self, path: str, max_depth=2) -> list[str]:
        return list_dir(path, max_depth)

    def read_file(self, path: str) -> str:
        with open(path, encoding="utf-8") as f:
            return f.read()

    def write_file(self, path: str, content: str, append: bool = False) -> None:
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)

    def update_file(self, path: str, content: bytes) -> None:
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
