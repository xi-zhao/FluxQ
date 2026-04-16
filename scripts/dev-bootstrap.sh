#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="all"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MIRROR=""
PIP_TIMEOUT="${PIP_TIMEOUT:-600}"

usage() {
  cat <<'EOF'
Usage: ./scripts/dev-bootstrap.sh [install|verify|all] [--python PATH] [--mirror tsinghua|aliyun|URL]

Bootstrap or verify the local FluxQ development environment.

Actions:
  install    Create .venv and install editable dev dependencies.
  verify     Run qrun version, Ruff, module-form MyPy, and full pytest -q smoke with the local .venv.
  all        Install dependencies and then run the full local smoke (default).

Options:
  --python PATH    Python interpreter to use for venv creation. Default: python3.11
  --mirror VALUE   Package index shortcut or explicit URL. Supports:
                   tsinghua -> https://pypi.tuna.tsinghua.edu.cn/simple
                   aliyun   -> https://mirrors.aliyun.com/pypi/simple
                   URL      -> any custom package index URL

Environment:
  PYTHON_BIN       Default Python interpreter if --python is omitted.
  PIP_TIMEOUT      Pip timeout in seconds. Default: 600
  PIP_INDEX_URL    Used as-is unless --mirror is provided.
EOF
}

log() {
  printf '==> %s\n' "$*"
}

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Required command not found: $1"
  fi
}

configure_mirror() {
  if [[ -z "$MIRROR" ]]; then
    return
  fi

  case "$MIRROR" in
    tsinghua)
      export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
      ;;
    aliyun)
      export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple"
      ;;
    *)
      export PIP_INDEX_URL="$MIRROR"
      ;;
  esac

  log "Using package index: $PIP_INDEX_URL"
}

install_deps() {
  require_command "$PYTHON_BIN"

  log "Creating virtual environment with $PYTHON_BIN"
  "$PYTHON_BIN" -m venv "$ROOT_DIR/.venv"

  log "Bootstrapping pip"
  "$ROOT_DIR/.venv/bin/python" -m ensurepip --upgrade

  log "Upgrading packaging tools"
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
    "$ROOT_DIR/.venv/bin/python" -m pip install --upgrade pip setuptools wheel --timeout "$PIP_TIMEOUT"

  log "Installing project and dev dependencies"
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
    "$ROOT_DIR/.venv/bin/python" -m pip install -e '.[dev,qiskit]' --timeout "$PIP_TIMEOUT"
}

verify_project() {
  if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
    fail "Local virtual environment is missing. Run './scripts/dev-bootstrap.sh install' first."
  fi

  log "Checking qrun version"
  "$ROOT_DIR/.venv/bin/qrun" version

  log "Running Ruff"
  "$ROOT_DIR/.venv/bin/ruff" check src tests

  if ! "$ROOT_DIR/.venv/bin/mypy" --version >/dev/null 2>&1; then
    log "Direct MyPy launcher failed under the current workspace path; continuing with '$ROOT_DIR/.venv/bin/python -m mypy'."
  fi

  log "Running MyPy via python -m mypy"
  "$ROOT_DIR/.venv/bin/python" -m mypy src

  log "Running full pytest smoke (pytest -q)"
  "$ROOT_DIR/.venv/bin/pytest" -q
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    install|verify|all)
      ACTION="$1"
      shift
      ;;
    --python)
      [[ $# -ge 2 ]] || fail "Missing value for --python"
      PYTHON_BIN="$2"
      shift 2
      ;;
    --mirror)
      [[ $# -ge 2 ]] || fail "Missing value for --mirror"
      MIRROR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      fail "Unknown argument: $1"
      ;;
  esac
done

cd "$ROOT_DIR"
configure_mirror

case "$ACTION" in
  install)
    install_deps
    ;;
  verify)
    verify_project
    ;;
  all)
    install_deps
    verify_project
    ;;
esac
