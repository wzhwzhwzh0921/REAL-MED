#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Kept as a function so mode selection can be checked without starting Docker.
detect_sandbox_mode() {
    python3 - "$PROJECT_ROOT/config.yaml" <<'PY'
import pathlib, re, sys
path = pathlib.Path(sys.argv[1])
text = path.read_text() if path.exists() else ''
block = re.search(r'^sandbox:\s*\n((?:[ \t]+[^\n]*\n?|[ \t]*\n)*)', text, re.M)
settings = block.group(1) if block else ''
provider = re.search(r'^\s+use:\s*([^#\n]+)', settings, re.M)
if not provider or 'AioSandboxProvider' not in provider.group(1):
    print('local')
else:
    remote = re.search(r'^\s+provisioner_url:\s*[^#\s]+', settings, re.M)
    print('provisioner' if remote else 'aio')
PY
}

main() {
    export DEER_FLOW_ROOT="$PROJECT_ROOT"
    local mode
    mode="$(detect_sandbox_mode)"
    local args=(-f "$PROJECT_ROOT/docker/docker-compose-dev.yaml")
    if [[ "$mode" == provisioner ]]; then
        args+=(--profile provisioner)
    fi
    case "${1:-start}" in
        start) docker compose "${args[@]}" up -d --build ;;
        stop) docker compose "${args[@]}" down ;;
        logs) docker compose "${args[@]}" logs -f ;;
        *) printf 'Usage: %s {start|stop|logs}\n' "$0" >&2; return 2 ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
