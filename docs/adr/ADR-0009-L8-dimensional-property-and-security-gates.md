# ADR-0009: L8 Quantitative Dimensional Invariants, Property Testing & Security Gates

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** `L8` Verification, Correctness & Supply-Chain Security
- **Evidence Grade:** E3 (Property-Tested & Audited)
- **Revisit Trigger:** 2027-01-01 or new Trail of Bits / Anthropic review plugin release

## Context and Problem Statement

Trading-engine defects overwhelmingly stem from dimensional/scaling bugs (bps vs percent vs decimal, shares vs notional, UTC vs `America/New_York`, split-unadjusted vs adjusted prices), non-monotonic stop ratchets, silent fallback defaults, and unreviewed dependency scripts.

## Decision Outcome

1. **Trail of Bits Quantitative & Security Suite (`trailofbits/skills` @ `149d7b21f4067765b82e67029730b42d228ef4b4`):**
   - `dimensional-analysis` (`v3.2.0`): Audits unit, tick, decimal, and basis-point scaling invariants.
   - `property-based-testing` (`v1.2.3`): Enforces `Hypothesis` (`6.170.15`) property invariants on order sizing, stop ratchets, and PnL accounting.
   - `spec-to-code-compliance` (`v2.0.2`): One-agent-per-requirement verification against ADRs and study specs.
   - `sharp-edges` (`v1.1.3`), `insecure-defaults` (`v2.0.3`), `supply-chain-risk-auditor` (`v2.0.4`), `fp-check` (`v1.0.5`), and `goal-prompt` (`v0.1.2`).
2. **Multi-Phase Security Audit (`cloudflare/security-audit-skill` @ `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8`):** Vendored verbatim into `.agents/skills/security-audit` for machine-readable security audits.
3. **Official PR & Static Gates (`anthropics/claude-plugins-official` @ `fd30cee3` + `mise`):** Enable `code-review`, `pr-review-toolkit`, `claude-security`, `commit-commands`, `plugin-dev`, `mcp-server-dev`, and `skill-creator`, backed by deterministic `ruff` (`0.17.5`), `ty` (`0.0.104`), `pyright`, `shellcheck` (`0.11.0`), and `actionlint` (`1.7.12`).

## Alternatives Considered

- **Prose-only code review checklists:** Insufficient without property-based fuzzing (`Hypothesis`), static AST/type gates (`ty` + `pyright`), and dedicated dimensional-analysis passes.

## Verification Witness

- `tests/test_sota_ecosystem.py::test_property_ratchet_never_loosens_stop` (`Hypothesis`), `ruff check .`, `ty check`, `pyright`, `shellcheck`, and `actionlint`.
