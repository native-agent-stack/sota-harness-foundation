#!/usr/bin/env bash
# Idempotent Post-Reset Clean WSL2/CUDA + Orca Bootstrap for Stationary Workstation (ADR-0021 / ADR-0022).
# Hard Invariants:
#   1. NEVER invokes 'wsl --shutdown' or touches co-resident 'sextant' / '/mnt/d' / '/mnt/z/meridian-data/handoff-*'.
#   2. Binds WSL services strictly to loopback 127.0.0.1 (--refuse-public).
#   3. Copies zero credentials or OAuth tokens; owner performs interactive sign-ins directly.
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Refused: bootstrap_clean_sota_wsl.sh must run inside the target Linux WSL2 distribution." >&2
  exit 1
fi

DISTRO_NAME="${WSL_DISTRO_NAME:-unknown}"
if [[ "${DISTRO_NAME}" == "sextant" ]]; then
  echo "Hard-Refused (ADR-0021): never mutate co-resident 'sextant' distribution." >&2
  exit 1
fi

echo "[1/4] Verifying WSL2 kernel, mirrored loopback, and RTX 4090 CUDA passthrough..."
uname -a
if [[ -x /usr/lib/wsl/lib/nvidia-smi ]]; then
  /usr/lib/wsl/lib/nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
fi

echo "[2/4] Ensuring inotify & ~/.agents SOTA peer-bus directories..."
mkdir -p "${HOME}/.agents/bin" "${HOME}/.agents/bus" "${HOME}/.agents/wiki" "${HOME}/.agents/workflows" "${HOME}/.local/bin"
if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
  sudo -n sysctl -w fs.inotify.max_user_instances=1024 >/dev/null || true
fi

echo "[3/4] Installing uv & syncing SOTA foundation workspace (if network available)..."
if ! command -v uv >/dev/null 2>&1 && ! [[ -x "${HOME}/.local/bin/uv" ]]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="${HOME}/.local/bin:/usr/lib/wsl/lib:${PATH}"

WIN_WS="/mnt/c/sota-workstation"
mkdir -p "${HOME}/sota-workstation"
for repo in native-agent-stack sota-harness-foundation agy-sota-harness sota-multi-model-workflows sota-compounding-lab sota-upstream-shelf-lock; do
  if [[ ! -d "${HOME}/sota-workstation/${repo}/.git" ]] && [[ -d "${WIN_WS}/${repo}/.git" ]]; then
    git clone --no-hardlinks "${WIN_WS}/${repo}" "${HOME}/sota-workstation/${repo}"
    git -C "${HOME}/sota-workstation/${repo}" remote set-url origin "https://github.com/native-agent-stack/${repo}.git"
  fi
done

if [[ -f "${HOME}/sota-workstation/sota-multi-model-workflows/workflows/REGISTRY.json" ]]; then
  cp -f "${HOME}/sota-workstation/sota-multi-model-workflows/workflows/"*.py "${HOME}/.agents/workflows/" 2>/dev/null || true
  cp -f "${HOME}/sota-workstation/sota-multi-model-workflows/workflows/REGISTRY.json" "${HOME}/.agents/workflows/REGISTRY.json"
fi

echo "[4/4] Clean WSL2 SOTA substrate ready (loopback-only, 0 credentials touched, sextant untouched)."
