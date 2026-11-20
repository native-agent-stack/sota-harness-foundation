# ADR-0046: Hard `upstream-map.toml` Provenance & SkillEvaluator ADR-0023 Banned-Quant-Library Gate

- **Status:** Accepted
- **Date:** 2026-11-20
- **Layer:** L9 / L10 Governance (`upstream-map.toml`, `src/cc_sota_harness/redteam_and_skill_eval.py`, enforcing `sota-upstream-shelf-lock ADR-0023` across `8` active runtimes and `60` canonical skills)
- **Evidence Grade:** E4 (`pytest`, `ruff check`, `scripts/architecture_catalog.py --check`, `shelf_lock.hard_upstream_rule --repo .`, `evaluate_skills.py --check-mounts` `60/60 PASS` across `8/8` runtime mounts, `gitleaks 0` leaks)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/native-agent-stack/sota-upstream-shelf-lock, https://github.com/nautechsystems/nautilus_trader, https://github.com/nkaz001/hftbacktest, https://github.com/stablyai/orca
- **Revisit Trigger:** Addition of any new module in `src/` or `scripts/`, or bump of the `18` pinned upstreams in `~/Documents/upstream/PINS.md`.

## Context and Problem Statement
Enforcing `ADR-0023` across the entire 18-repository ecosystem and 60-skill / 8-runtime fleet requires `sota-harness-foundation` itself to declare 100% file-level upstream provenance in `upstream-map.toml` AND extend `redteam_and_skill_eval.py` (`SkillEvaluator`) to flag banned low-quality backtest/quant libraries (`backtrader`, `backtesting.py`, `mlfinlab`, `tcapy`, `vollib`, `tradingview_ta`, `pandas-datareader`) as `P1` blockers and legacy `yfinance` data fallbacks as `P2` remediation warnings.

## Decision Outcome
1. Add `upstream-map.toml` mapping 100% of tracked `src/` and `scripts/` files to pinned SOTA upstreams in `UPSTREAM.md` and the 18-repo `[shelf_pins]` table.
2. Extend `src/cc_sota_harness/redteam_and_skill_eval.py` with `BANNED_BACKTEST_ENGINE_SLUGS` (`P1` fail-closed) and `DEPRECATED_DATA_LIB_SLUGS` (`P2` warning) enforced on every skill and red-team audit.

## Alternatives Considered
- **Leave `sota-harness-foundation` without `upstream-map.toml`:** Rejected because `ADR-0023` requires 100% (`18/18`) ecosystem coverage without exemptions.

## Verification Witness
- Verified locally with `pytest -q`, `ruff check`, `scripts/architecture_catalog.py --check`, `shelf_lock.hard_upstream_rule --repo .`, `evaluate_skills.py --check-mounts` (`60/60 PASS` across `8/8` runtime mounts), and `gitleaks protect --staged --no-banner` (`0` leaks).
