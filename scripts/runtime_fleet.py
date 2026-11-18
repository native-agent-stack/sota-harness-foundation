#!/usr/bin/env python3
"""Inspect and validate the CC Lead Multi-Model Routing & Runtime Ecosystem Matrix.

Validates config/multi-model-routing.json invariants (Artificial Analysis v5.0.1 /
Coding Agent Index v2.1 leadership, OMC/OMO Hephaestus non-GPT constraint, one-model-per-session
prompt-cache rule, paper-only firewall) and probes all installed multi-model CLI binaries.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ROUTING_CONFIG = REPO_ROOT / "config" / "multi-model-routing.json"

EXTRA_SEARCH_DIRS = [
    pathlib.Path.home() / ".local" / "share" / "mise" / "shims",
    pathlib.Path.home() / ".local" / "bin",
]


def resolve_binary(bin_name: str) -> str | None:
    path_env = os.environ.get("PATH", "")
    augmented_path = os.pathsep.join([*(str(p) for p in EXTRA_SEARCH_DIRS), path_env])
    found = shutil.which(bin_name, path=augmented_path)
    if found:
        return found
    probe = subprocess.run(
        ["mise", "which", bin_name],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        timeout=8,
        check=False,
    )
    if probe.returncode == 0 and probe.stdout.strip():
        return probe.stdout.strip()
    return None


def validate_routing_matrix(*, config_only: bool = False) -> tuple[dict, list[str]]:
    errors: list[str] = []
    if not ROUTING_CONFIG.is_file():
        return {}, [f"Missing routing config: {ROUTING_CONFIG}"]

    cfg = json.loads(ROUTING_CONFIG.read_text())
    invariants = cfg.get("invariants", {})
    if invariants.get("oneModelPerConversation") is not True:
        errors.append("oneModelPerConversation invariant must be true")
    if invariants.get("hephaestusForbidsGptModels") is not True:
        errors.append("hephaestusForbidsGptModels invariant must be true")
    if invariants.get("paperOnlyTradingFirewall") is not True:
        errors.append("paperOnlyTradingFirewall invariant must be true")
    if invariants.get("studyWallDate") != "2026-10-15":
        errors.append(f"Unexpected studyWallDate: {invariants.get('studyWallDate')}")

    cc_lead = cfg.get("ccLead", {})
    if cc_lead.get("defaultModelId") != "claude-fable-5-2" or cc_lead.get("effortLevel") != "xhigh":
        errors.append("CC Lead must target claude-fable-5-2 at effortLevel=xhigh")

    models = {m["id"]: m for m in cfg.get("frontierModels", [])}
    for required_model in (
        "claude-fable-5-2",
        "gpt-6.2-astra",
        "gpt-6.2-sol",
        "gemini-4-carbon-high",
        "claude-opus-5-5",
        "claude-sonnet-5-5",
        "claude-haiku-5-5",
        "deepseek-v4-pro",
        "kimi-k3.1-pro",
    ):
        if required_model not in models:
            errors.append(f"Missing frontier model in catalog: {required_model}")

    agent_matrix = cfg.get("omcOmoAgentMatrix", {})
    heph = agent_matrix.get("Hephaestus", {})
    for slot in ("premiumModel", "balancedModel"):
        chosen = str(heph.get(slot, ""))
        if chosen.startswith("gpt-"):
            errors.append(f"Hephaestus {slot} violates non-GPT rule: {chosen}")

    for route in cfg.get("taskRouting", []):
        for key in ("primaryModel", "challengerModel"):
            m_id = route.get(key)
            if m_id not in models:
                errors.append(f"Task route {route.get('taskClass')} references unknown model {m_id}")

    resolved_runtimes: list[dict[str, str | None]] = []
    for rt in cfg.get("installedRuntimes", []):
        bin_name = rt["binary"]
        resolved = None if config_only else resolve_binary(bin_name)
        resolved_runtimes.append(
            {
                "name": rt["name"],
                "binary": bin_name,
                "orcaNativeAgent": rt.get("orcaNativeAgent"),
                "category": rt.get("category"),
                "resolvedPath": resolved,
            }
        )
        if not config_only and resolved is None:
            errors.append(f"Missing multi-model runtime binary: {bin_name} ({rt['name']})")

    summary = {
        "ok": len(errors) == 0,
        "benchmarkUrl": cfg.get("benchmarkSource", {}).get("url"),
        "ccLeadModel": f"{cc_lead.get('defaultModelId')} ({cc_lead.get('effortLevel')})",
        "frontierModelCount": len(models),
        "taskRouteCount": len(cfg.get("taskRouting", [])),
        "runtimeCount": len(resolved_runtimes),
        "runtimes": resolved_runtimes,
        "errors": errors,
    }
    return summary, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CC Lead multi-model routing & runtime binaries.")
    parser.add_argument(
        "--config-only", action="store_true", help="Validate routing schema without probing host binaries"
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    summary, errors = validate_routing_matrix(config_only=args.config_only)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        status = "PASS" if not errors else f"FAIL ({len(errors)})"
        print(
            f"[{status}] CC Lead={summary.get('ccLeadModel')} | "
            f"models={summary.get('frontierModelCount')} | "
            f"routes={summary.get('taskRouteCount')} | "
            f"runtimes={summary.get('runtimeCount')}"
        )
        for err in errors:
            print(f"  - {err}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
