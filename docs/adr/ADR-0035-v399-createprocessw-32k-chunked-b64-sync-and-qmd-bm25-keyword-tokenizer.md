# ADR-0035: `v3.9.9` Win32 `CreateProcessW` `32,767`-Char Chunked Base64 Relay, `@@ZB64:` Return Compression & `qmd` BM25 Keyword Tokenizer

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L2 / L3 / L7 / L8 / L10 (`P0–P5` × `T1–T5` × `H0–H7`)
- **Evidence Grade:** E4 (`35` ADRs, `63/63` Pytest & Hypothesis Property Tests, Live `cc-lead` `#173`/`#179` & `f2693e3b` `24h` Sync Audit Verified)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/stablyai/orca, https://github.com/tobi/qmd, https://github.com/native-agent-stack/sota-multi-model-workflows
- **Revisit Trigger:** Ecosystem `v4.0.0` promotion or `2026-12-06` `23/5` Consolidated SIP cutover

## Context and Problem Statement

Live cross-workstation testing (`f2693e3b` `--since-hours 24.0` + `cc-lead` `#173`/`#179`) exposed two deterministic transport/query boundaries in `v3.9.8` (`ADR-0034`):
1. `24`-hour memory delta bundles (`85` lessons + `96` hypotheses) produced `~127 KB` of Base64 code, exceeding Windows `CreateProcessW`'s `32,767`-character command-line ceiling on `pwsh.exe --command` and scrolling `> 800` lines in `orca terminal read`.
2. Passing `repo + goal[:60]` verbatim to `qmd search` cut tokens mid-word and caused multi-word BM25 queries on natural-language sentences to return `No results found`.

## Decision Outcome

1. **Ship `chunk_powershell_b64_payload()` (`<= 3,500`-char chunks) & Sliding-Window `<= 6h` Delta Sync:**
   - Keep every single command line strictly `< 4,000` chars (`<< 32,767` `CreateProcessW` limit) and compress return frames with `zlib` (`@@ZB64:`).
2. **Ship `tokenize_qmd_bm25_query()` Whole-Token Keyword Extractor:**
   - Strip conversational stopwords and preserve intact hyphenated identifiers (`ADR-0035`, `cc-sota-harness`, `OMC_RUNTIME_V2`) without mid-word slicing, paired with `2,325` embedded `qmd` vector chunks.

## Alternatives Considered

- **Truncating lessons/hypotheses count instead of chunking/windowing:** Rejected — loses historical audit completeness across surfaces.

## Verification Witness

- `uv run python scripts/architecture_catalog.py` & `--check` (`35 ADRs valid, 0 drift`), `uv run ruff check .`, `uv run pytest -q` (`63 passed`), and `gitleaks git --staged --no-banner` (`0` leaks).
