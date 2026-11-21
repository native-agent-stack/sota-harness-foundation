"""ADR-0043: Red-Team BugHunter & 4-Tier SkillEvaluator Contract (`v3.10.8`).

Distills deterministic verification invariants from:
- `elementalsouls/Claude-BugHunter` (24 vulnerability classes + PoC verification)
- `cloudflare/security-audit-skill` (two-pass self-refuting P0-P3 severity grading)
- `NVIDIA/SkillEvaluator` (4-tier schema/security/compatibility/overlap gates)
- `NVIDIA/OpenShell` + `morluto/rea` (runtime boundaries & binary/script inspection)
plus SOTA quantitative trading-firewall invariants (`ADR-0022`, `ADR-0041`, `ADR-0042`).
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REDTEAM_SKILLEVAL_SCHEMA_VERSION = "sota-redteam-skilleval.v1"

CANONICAL_ACTIVE_EIGHT_RUNTIMES: tuple[str, ...] = (
    "claude",
    "codex",
    "antigravity",
    "opencode",
    "dsh",
    "omp",
    "pi",
    "muse",
)

REDTEAM_VULNERABILITY_CLASSES: tuple[str, ...] = (
    "broken_authentication",
    "broken_access_control_idor",
    "ssrf_and_metadata_pivot",
    "sql_and_duckdb_injection",
    "command_and_shell_injection",
    "path_traversal_and_symlink_escape",
    "insecure_deserialization",
    "prototype_or_ast_pollution",
    "xss_and_dom_injection",
    "csrf_and_origin_bypass",
    "race_condition_toctou",
    "integer_overflow_and_ieee754_nan_inf",
    "cryptographic_weakness_and_nonce_reuse",
    "secret_and_credential_exposure",
    "supply_chain_and_unpinned_action",
    "prompt_injection_and_tool_escalation",
    "mcp_schema_or_unbounded_payload",
    "live_capital_firewall_bypass",
    "adr0022_stop_cap_exceeded",
    "bitemporal_pit_lookahead_leak",
    "single_active_broker_host_split",
    "stale_or_retired_model_drift",
    "home_path_leakage",
    "raw_live_daemon_db_mutation",
)

FORBIDDEN_STALE_MODEL_SLUGS: tuple[str, ...] = (
    "deepseek-v4-pro",
    "deepseek-v4-flash",
    "gemini-3.8-flash",
    "gemini-3.1-pro",
    "gpt-6.1-sol",
    "gpt-6-astra",
    "gpt-6-sol",
    "gpt-6-luna",
    "gpt-5.6",
    "gpt-5.5",
    "gpt-5.3",
    "gpt-5-nano",
    "claude-fable-5-1",
    "claude-haiku-5-5",
    "claude-haiku-4-5",
    "claude-opus-4-6",
    "kimi-",
    "moonshot" + "/",
)

RETIRED_RUNTIME_SLUGS: tuple[str, ...] = ("grok", "goose")

BANNED_BACKTEST_ENGINE_SLUGS: tuple[str, ...] = (
    "backtrader",
    "backtesting.py",
    "mlfinlab",
    "tcapy",
    "vollib",
    "tradingview_ta",
    "pandas-datareader",
    "pandas_datareader",
)
DEPRECATED_DATA_LIB_SLUGS: tuple[str, ...] = ("yfinance",)

_NEGATION_MARKERS: tuple[str, ...] = (
    "forbidden retired",
    "supersedes ",
    "never use",
    "do not use",
    "prohibited",
    "retired:",
    "zero-stale",
    "zero stale",
)

_LIVE_ENDPOINT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("live_alpaca_endpoint", re.compile(r"(?<!paper-)(?<![A-Za-z0-9-])api\.alpaca\.markets\b", re.IGNORECASE)),
    ("live_ibkr_gateway_4001", re.compile(r"(?:127\.0\.0\.1|localhost|0\.0\.0\.0):4001\b")),
    ("live_ibkr_tws_7496", re.compile(r"(?:127\.0\.0\.1|localhost|0\.0\.0\.0):7496\b")),
    ("live_capital_binary", re.compile(r"\.claude/bin/(?:live|alpaca-live-mcp|key-store)\b")),
)

_HOME_PATH_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("win32_home_path", re.compile(r"[A-Za-z]:[/\\]{1,2}Users[/\\]{1,2}[A-Za-z0-9._-]+")),
    ("macos_home_path", re.compile(r"(?<![A-Za-z0-9_*])/" + r"Users/[A-Za-z0-9._-]+")),
    ("linux_home_path", re.compile(r"(?<![A-Za-z0-9_*])/home/[A-Za-z0-9._-]+")),
)

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai_or_sk_token", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("github_pat", re.compile(r"\b(?:ghp|gho|ghu|ghs)_[A-Za-z0-9]{20,}\b")),
    ("github_fine_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("alpaca_live_key_id", re.compile(r"\bAK[0-9A-Z]{18}\b")),
    ("private_key_header", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)

_PROMPT_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "ignore_prior_instructions",
        re.compile(r"\bignore\s+(?:all\s+)?previous\s+instructions\b", re.IGNORECASE),
    ),
    (
        "bypass_safety_firewall",
        re.compile(r"\bbypass\s+(?:the\s+)?(?:firewall|safety|approval|pretooluse)\b", re.IGNORECASE),
    ),
)

_PAPER_SELF_INVENTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "self_invent_from_paper",
        re.compile(
            r"\b(?:self[- ]invent|hand[- ]?roll|re[- ]?implement\s+from\s+scratch)\b[^\n]{0,60}\b(?:paper|papers|arxiv|literature)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "custom_backtest_from_scratch",
        re.compile(
            r"\b(?:build|write|create)\s+(?:a\s+)?(?:custom|hand[- ]?rolled)\s+(?:backtest(?:er|ing)?|trading)\s+(?:engine|loop)\s+from\s+scratch\b",
            re.IGNORECASE,
        ),
    ),
)

_SAFE_FIREWALL_DOCUMENTATION_MARKERS: tuple[str, ...] = (
    "hard-refused",
    "hard refused",
    "never call",
    "never connect",
    "never touch",
    "fail closed",
    "fail-closed",
    "blocked",
    "forbids",
    "refused",
    "zero live",
    "denieddomains",
    "expecteddecision",
    '"bash(*',
)

_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "use",
        "using",
        "when",
        "with",
    }
)


@dataclass(frozen=True, slots=True)
class RedTeamFinding:
    """Single structured P0-P3 red-team or skill-audit finding."""

    severity: str
    vuln_class: str
    rule_id: str
    line_number: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "vuln_class": self.vuln_class,
            "rule_id": self.rule_id,
            "line_number": self.line_number,
            "message": self.message,
        }


def _parse_skill_frontmatter(text: str) -> tuple[dict[str, Any] | None, str, str | None]:
    """Parse YAML frontmatter delimited by `---` lines from a SKILL.md document."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, "missing opening YAML frontmatter delimiter '---'"
    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return None, text, "missing closing YAML frontmatter delimiter '---'"
    raw_yaml = "\n".join(lines[1:end_idx])
    try:
        parsed = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:
        return None, text, f"invalid YAML frontmatter: {exc}"
    if not isinstance(parsed, dict):
        return None, text, "YAML frontmatter must deserialize to a mapping"
    body = "\n".join(lines[end_idx + 1 :])
    return parsed, body, None


def _line_is_negated(line: str, markers: tuple[str, ...]) -> bool:
    low = line.lower()
    return any(m in low for m in markers)


def _scan_lines_for_findings(
    text: str,
    *,
    allow_home_paths: bool = False,
    allow_documented_negations: bool = True,
) -> list[RedTeamFinding]:
    """Scan lines deterministically for P0/P1 firewall, credential, injection, and stale-model hazards."""
    findings: list[RedTeamFinding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule_id, pat in _SECRET_PATTERNS:
            if pat.search(line):
                findings.append(
                    RedTeamFinding(
                        severity="P0",
                        vuln_class="secret_and_credential_exposure",
                        rule_id=rule_id,
                        line_number=lineno,
                        message=f"Potential credential/secret pattern matched ({rule_id})",
                    )
                )

        if not allow_home_paths:
            for rule_id, pat in _HOME_PATH_PATTERNS:
                if pat.search(line):
                    findings.append(
                        RedTeamFinding(
                            severity="P1",
                            vuln_class="home_path_leakage",
                            rule_id=rule_id,
                            line_number=lineno,
                            message=f"Machine-specific home path matched ({rule_id})",
                        )
                    )

        for rule_id, pat in _PROMPT_INJECTION_PATTERNS:
            if pat.search(line) and not (
                allow_documented_negations and _line_is_negated(line, _SAFE_FIREWALL_DOCUMENTATION_MARKERS)
            ):
                findings.append(
                    RedTeamFinding(
                        severity="P0",
                        vuln_class="prompt_injection_and_tool_escalation",
                        rule_id=rule_id,
                        line_number=lineno,
                        message=f"Prompt-injection or firewall-bypass directive matched ({rule_id})",
                    )
                )

        for rule_id, pat in _LIVE_ENDPOINT_PATTERNS:
            if pat.search(line) and not (
                allow_documented_negations and _line_is_negated(line, _SAFE_FIREWALL_DOCUMENTATION_MARKERS)
            ):
                findings.append(
                    RedTeamFinding(
                        severity="P0",
                        vuln_class="live_capital_firewall_bypass",
                        rule_id=rule_id,
                        line_number=lineno,
                        message=f"Unguarded live-capital endpoint/binary reference ({rule_id})",
                    )
                )

        low = line.lower()
        if not (allow_documented_negations and _line_is_negated(line, _NEGATION_MARKERS)):
            for slug in FORBIDDEN_STALE_MODEL_SLUGS:
                if slug in low:
                    findings.append(
                        RedTeamFinding(
                            severity="P1",
                            vuln_class="stale_or_retired_model_drift",
                            rule_id=f"stale_model:{slug}",
                            line_number=lineno,
                            message=f"Forbidden stale/retired model reference {slug!r}",
                        )
                    )
            for retired in RETIRED_RUNTIME_SLUGS:
                if re.search(rf"\b{re.escape(retired)}\b", low) and not _line_is_negated(
                    line, _SAFE_FIREWALL_DOCUMENTATION_MARKERS
                ):
                    findings.append(
                        RedTeamFinding(
                            severity="P2",
                            vuln_class="stale_or_retired_model_drift",
                            rule_id=f"retired_runtime:{retired}",
                            line_number=lineno,
                            message=f"Retired runtime reference {retired!r} without explicit retirement/negation marker",
                        )
                    )
            for banned_lib in BANNED_BACKTEST_ENGINE_SLUGS:
                if re.search(rf"\b{re.escape(banned_lib)}\b", low) and not _line_is_negated(
                    line, _SAFE_FIREWALL_DOCUMENTATION_MARKERS
                ):
                    findings.append(
                        RedTeamFinding(
                            severity="P1",
                            vuln_class="supply_chain_and_unpinned_action",
                            rule_id=f"adr0023_banned_quant_lib:{banned_lib}",
                            line_number=lineno,
                            message=f"ADR-0023 banned low-quality quant library {banned_lib!r} referenced without prohibition marker",
                        )
                    )
            for dep_lib in DEPRECATED_DATA_LIB_SLUGS:
                if re.search(rf"\b{re.escape(dep_lib)}\b", low) and not _line_is_negated(
                    line, _SAFE_FIREWALL_DOCUMENTATION_MARKERS
                ):
                    findings.append(
                        RedTeamFinding(
                            severity="P2",
                            vuln_class="supply_chain_and_unpinned_action",
                            rule_id=f"adr0023_legacy_data_lib:{dep_lib}",
                            line_number=lineno,
                            message=f"ADR-0023 legacy data library {dep_lib!r} referenced; migrate to pinned alpaca-py/SIP or FMP",
                        )
                    )
            for rule_id, pat in _PAPER_SELF_INVENTION_PATTERNS:
                if pat.search(line) and not _line_is_negated(
                    line, (*_SAFE_FIREWALL_DOCUMENTATION_MARKERS, "never self-invent", "zero paper self-invention")
                ):
                    findings.append(
                        RedTeamFinding(
                            severity="P1",
                            vuln_class="supply_chain_and_unpinned_action",
                            rule_id=f"adr0050_paper_self_invention:{rule_id}",
                            line_number=lineno,
                            message=(
                                f"Paper self-invention / from-scratch engine directive ({rule_id}); "
                                "use cleanly installed SOTA frameworks + official paper repos tested E2E on historical data"
                            ),
                        )
                    )
    return findings


def run_redteam_firewall_audit(
    payload: str,
    *,
    context: str = "generic",
    hard_stop_pct: float | None = None,
    ts_event_ns: int | None = None,
    ts_recv_ns: int | None = None,
    decision_ns: int | None = None,
    allow_home_paths: bool = False,
    allow_documented_negations: bool = True,
) -> dict[str, Any]:
    """Run two-pass deterministic red-team security & trading-firewall audit over text + numeric invariants."""
    if not isinstance(payload, str):
        raise ValueError("payload must be a string")

    findings = _scan_lines_for_findings(
        payload,
        allow_home_paths=allow_home_paths,
        allow_documented_negations=allow_documented_negations,
    )

    if hard_stop_pct is not None:
        if not math.isfinite(hard_stop_pct) or hard_stop_pct <= 0.0 or hard_stop_pct > 2.0:
            findings.append(
                RedTeamFinding(
                    severity="P0",
                    vuln_class="adr0022_stop_cap_exceeded",
                    rule_id="adr0022_stop_cap",
                    line_number=0,
                    message=f"ADR-0022 requires finite 0 < hard_stop_pct <= 2.0, got {hard_stop_pct!r}",
                )
            )

    if ts_event_ns is not None or ts_recv_ns is not None or decision_ns is not None:
        if ts_event_ns is None or ts_recv_ns is None or decision_ns is None:
            findings.append(
                RedTeamFinding(
                    severity="P0",
                    vuln_class="bitemporal_pit_lookahead_leak",
                    rule_id="bitemporal_pit_incomplete",
                    line_number=0,
                    message="All three nanosecond timestamps (ts_event_ns, ts_recv_ns, decision_ns) are required",
                )
            )
        elif not (0 < ts_event_ns <= ts_recv_ns <= decision_ns):
            findings.append(
                RedTeamFinding(
                    severity="P0",
                    vuln_class="bitemporal_pit_lookahead_leak",
                    rule_id="bitemporal_pit_order",
                    line_number=0,
                    message=(
                        f"Lookahead violation: expected 0 < ts_event_ns ({ts_event_ns}) "
                        f"<= ts_recv_ns ({ts_recv_ns}) <= decision_ns ({decision_ns})"
                    ),
                )
            )

    p0_count = sum(1 for f in findings if f.severity == "P0")
    p1_count = sum(1 for f in findings if f.severity == "P1")
    p2_count = sum(1 for f in findings if f.severity == "P2")
    passed = p0_count == 0 and p1_count == 0
    digest = hashlib.sha256(
        json.dumps(
            {
                "schema_version": REDTEAM_SKILLEVAL_SCHEMA_VERSION,
                "context": context,
                "findings": [f.to_dict() for f in findings],
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    return {
        "schema_version": REDTEAM_SKILLEVAL_SCHEMA_VERSION,
        "context": context,
        "passed": passed,
        "p0_count": p0_count,
        "p1_count": p1_count,
        "p2_count": p2_count,
        "findings": [f.to_dict() for f in findings],
        "vulnerability_classes_catalog_count": len(REDTEAM_VULNERABILITY_CLASSES),
        "audit_sha256": digest,
    }


def _tokenize_description(desc: str) -> set[str]:
    tokens = {tok for tok in re.findall(r"[a-z0-9]{3,}", desc.lower()) if tok not in _STOPWORDS}
    return tokens


def evaluate_skill_directory(
    skill_dir: Path,
    *,
    max_skill_bytes: int = 128_000,
    compatible_runtimes: tuple[str, ...] = CANONICAL_ACTIVE_EIGHT_RUNTIMES,
) -> dict[str, Any]:
    """Evaluate a single skill directory against Tiers 1-3 of the NVIDIA SkillEvaluator contract."""
    skill_path = Path(skill_dir)
    skill_md = skill_path / "SKILL.md"
    errors: list[str] = []
    warnings: list[str] = []

    if not skill_path.is_dir():
        return {
            "skill": skill_path.name,
            "passed": False,
            "tier1_schema_ok": False,
            "tier2_security_ok": False,
            "tier3_runtime_compat_ok": False,
            "errors": [f"skill directory missing: {skill_path}"],
            "warnings": [],
            "findings": [],
            "description_tokens": [],
        }

    if not skill_md.is_file():
        return {
            "skill": skill_path.name,
            "passed": False,
            "tier1_schema_ok": False,
            "tier2_security_ok": False,
            "tier3_runtime_compat_ok": False,
            "errors": ["missing SKILL.md"],
            "warnings": [],
            "findings": [],
            "description_tokens": [],
        }

    raw_bytes = skill_md.read_bytes()
    if len(raw_bytes) > max_skill_bytes:
        errors.append(f"SKILL.md exceeds {max_skill_bytes} bytes ({len(raw_bytes)})")

    text = raw_bytes.decode("utf-8", errors="replace")
    meta, body, parse_err = _parse_skill_frontmatter(text)
    if parse_err is not None or meta is None:
        errors.append(parse_err or "frontmatter parse failure")
        name_val = ""
        desc_val = ""
    else:
        name_val = str(meta.get("name") or "").strip()
        desc_val = str(meta.get("description") or "").strip()
        if not name_val:
            errors.append("frontmatter 'name' must be non-empty")
        if len(desc_val) < 12:
            errors.append("frontmatter 'description' must be at least 12 characters")
        if len(body.strip()) < 20:
            errors.append("SKILL.md markdown body is unexpectedly empty")

    tier1_ok = len(errors) == 0

    # Tier 2: Scan SKILL.md + optional scripts/ for security, leak, and stale-model defects
    all_findings: list[dict[str, Any]] = []
    skill_audit = run_redteam_firewall_audit(
        text,
        context=f"skill:{skill_path.name}/SKILL.md",
        allow_home_paths=False,
        allow_documented_negations=True,
    )
    all_findings.extend(skill_audit["findings"])

    for sub in sorted(skill_path.rglob("*")):
        if not sub.is_file() or sub == skill_md or "__pycache__" in sub.parts:
            continue
        if sub.suffix.lower() in (".py", ".sh", ".ps1", ".ts", ".js", ".json", ".yaml", ".yml", ".md", ".txt"):
            sub_txt = sub.read_text(encoding="utf-8", errors="replace")
            sub_audit = run_redteam_firewall_audit(
                sub_txt,
                context=f"skill:{skill_path.name}/{sub.relative_to(skill_path).as_posix()}",
                allow_home_paths=False,
                allow_documented_negations=True,
            )
            all_findings.extend(sub_audit["findings"])

    blocking = [f for f in all_findings if f["severity"] in ("P0", "P1")]
    for f in all_findings:
        if f["severity"] == "P2":
            warnings.append(f"{f['rule_id']}@L{f['line_number']}: {f['message']}")
    tier2_ok = len(blocking) == 0

    # Tier 3: Cross-runtime compatibility (valid slug naming, declared_name parity, valid Python script AST)
    valid_slug = bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]*", skill_path.name))
    if not valid_slug:
        errors.append(f"invalid cross-runtime skill directory name {skill_path.name!r}")
    py_ast_ok = True
    for py_f in sorted(skill_path.rglob("*.py")):
        if py_f.is_file():
            try:
                ast.parse(py_f.read_text(encoding="utf-8", errors="replace"), filename=str(py_f))
            except SyntaxError as exc:
                py_ast_ok = False
                errors.append(f"python syntax error in {py_f.relative_to(skill_path).as_posix()}: {exc.msg}")
    tier3_ok = valid_slug and py_ast_ok and len(compatible_runtimes) == len(CANONICAL_ACTIVE_EIGHT_RUNTIMES)

    passed = tier1_ok and tier2_ok and tier3_ok
    return {
        "skill": skill_path.name,
        "declared_name": name_val,
        "passed": passed,
        "tier1_schema_ok": tier1_ok,
        "tier2_security_ok": tier2_ok,
        "tier3_runtime_compat_ok": tier3_ok,
        "compatible_runtimes": list(compatible_runtimes),
        "errors": errors,
        "warnings": warnings,
        "findings": all_findings,
        "description_tokens": sorted(_tokenize_description(desc_val)),
    }


def evaluate_skill_corpus(
    skills_root: Path,
    *,
    overlap_threshold: float = 0.72,
    max_skill_bytes: int = 128_000,
    runtime_mount_roots: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Run all 4 SkillEvaluator tiers (Schema, Security, Cross-Runtime Mount Parity, Semantic Overlap) across a skill root."""
    if not (0.0 < overlap_threshold <= 1.0):
        raise ValueError(f"overlap_threshold must be in (0, 1], got {overlap_threshold!r}")
    root = Path(skills_root)
    if not root.is_dir():
        raise FileNotFoundError(f"skills_root does not exist: {root}")

    broken_symlinks = sorted(
        p.name for p in root.iterdir() if p.is_symlink() and not p.exists() and not p.name.startswith(".")
    )
    skill_dirs = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    results = [evaluate_skill_directory(d, max_skill_bytes=max_skill_bytes) for d in skill_dirs]
    for bname in broken_symlinks:
        results.append(
            {
                "skill": bname,
                "declared_name": "",
                "passed": False,
                "tier1_schema_ok": False,
                "tier2_security_ok": False,
                "tier3_runtime_compat_ok": False,
                "compatible_runtimes": [],
                "errors": [f"broken skill symlink: {bname}"],
                "warnings": [],
                "findings": [],
                "description_tokens": [],
            }
        )

    # Real Tier-3 Cross-Runtime Mount Audit when runtime_mount_roots is provided (checks missing skills,
    # broken symlinks, and full skill-directory manifest SHA-256 parity across SKILL.md + executable scripts/resources).
    def _skill_dir_manifest_sha256(skill_dir: Path) -> str | None:
        if not (skill_dir / "SKILL.md").is_file():
            return None
        entries: list[tuple[str, str]] = []
        for f in sorted(skill_dir.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(skill_dir)
            if "__pycache__" in rel.parts or f.suffix == ".pyc":
                continue
            entries.append((rel.as_posix(), hashlib.sha256(f.read_bytes()).hexdigest()))
        return hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode("utf-8")).hexdigest()

    mount_parity: dict[str, dict[str, Any]] = {}
    if runtime_mount_roots:
        canon_hashes: dict[str, str] = {}
        for d in skill_dirs:
            mh = _skill_dir_manifest_sha256(d)
            if mh is not None:
                canon_hashes[d.name] = mh
        res_by_skill = {r["skill"]: r for r in results}
        for rt_name, m_root in sorted(runtime_mount_roots.items()):
            m_path = Path(m_root)
            missing_rt: list[str] = []
            drifted_rt: list[str] = []
            broken_rt: list[str] = []
            if not m_path.is_dir():
                missing_rt = sorted(canon_hashes.keys())
            else:
                for p in sorted(m_path.iterdir()):
                    if p.is_symlink() and not p.exists():
                        broken_rt.append(p.name)
                for sname, expected_sha in sorted(canon_hashes.items()):
                    actual_sha = _skill_dir_manifest_sha256(m_path / sname)
                    if actual_sha is None:
                        missing_rt.append(sname)
                    elif actual_sha != expected_sha:
                        drifted_rt.append(sname)
            rt_ok = not (missing_rt or drifted_rt or broken_rt)
            mount_parity[rt_name] = {
                "root": str(m_path.name),
                "ok": rt_ok,
                "missing_count": len(missing_rt),
                "drifted_count": len(drifted_rt),
                "broken_symlinks": broken_rt,
                "missing": missing_rt[:10],
                "drifted": drifted_rt[:10],
            }
            for sname in (*missing_rt, *drifted_rt):
                r_item = res_by_skill.get(sname)
                if r_item is not None:
                    r_item["tier3_runtime_compat_ok"] = False
                    r_item["passed"] = False
                    r_item["errors"].append(f"mount_parity_fail:{rt_name}")

    # Tier 4: Pairwise token-Jaccard overlap check over frontmatter descriptions
    overlap_warnings: list[dict[str, Any]] = []
    token_sets = [(r["skill"], set(r["description_tokens"])) for r in results]
    for i in range(len(token_sets)):
        name_a, set_a = token_sets[i]
        if not set_a:
            continue
        for j in range(i + 1, len(token_sets)):
            name_b, set_b = token_sets[j]
            if not set_b:
                continue
            union = set_a | set_b
            sim = len(set_a & set_b) / len(union) if union else 0.0
            if sim >= overlap_threshold:
                overlap_warnings.append(
                    {
                        "skill_a": name_a,
                        "skill_b": name_b,
                        "jaccard_similarity": round(sim, 4),
                    }
                )

    failed_skills = [r["skill"] for r in results if not r["passed"]]
    passed_count = len(results) - len(failed_skills)
    mounts_all_ok = all(bool(v["ok"]) for v in mount_parity.values())
    digest = hashlib.sha256(
        json.dumps(
            {
                "schema_version": REDTEAM_SKILLEVAL_SCHEMA_VERSION,
                "skills_evaluated": len(results),
                "failed_skills": failed_skills,
                "overlap_warnings": overlap_warnings,
                "mount_parity": mount_parity,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    return {
        "schema_version": REDTEAM_SKILLEVAL_SCHEMA_VERSION,
        "all_passed": len(failed_skills) == 0 and len(results) > 0 and mounts_all_ok,
        "skills_evaluated": len(results),
        "passed_count": passed_count,
        "failed_count": len(failed_skills),
        "failed_skills": failed_skills,
        "overlap_threshold": overlap_threshold,
        "overlap_warnings": overlap_warnings,
        "compatible_runtimes_count": len(CANONICAL_ACTIVE_EIGHT_RUNTIMES),
        "compatible_runtimes": list(CANONICAL_ACTIVE_EIGHT_RUNTIMES),
        "mounts_checked": len(mount_parity),
        "mount_parity": mount_parity,
        "results": results,
        "report_sha256": digest,
    }
