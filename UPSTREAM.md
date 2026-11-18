# Upstream SOTA Frameworks & 18-Pin Quantitative Shelf Lineage (`v3.9.0`)

Every layer (`L0–L13`), Trading Lane (`T1–T5`), and Harness Lane (`H0–H7`) in `native-agent-stack/sota-harness-foundation` builds directly on pinned primary-source upstream repositories (`ADR-0001`, `ADR-0022`, `ADR-0029`, `ADR-0031`).

## 1. Multi-Model Runtime Workers & 8 SOTA Orchestration Frameworks (`17` Binaries, `7` Vendors)

| Framework Layer | Upstream Repository | Role & Verified Contract |
| :--- | :--- | :--- |
| Cross-Machine Supervisor | `https://github.com/stablyai/orca` (`v1.4.261`) | Symmetric `:6770` `Mac M5 Max <-> Noesis` E2EE mesh, `--kind folder` `trading-lanes`/`harness-lanes` hubs (`sota-orca-lane-hub.v2`), `worker-start --on 100.110.115.22` |
| Sovereign Lead Orchestrator | `https://github.com/Yeachan-Heo/oh-my-claudecode` (`v5.8.4`) | `claude-fable-5-2` (`xhigh`, `OMC_RUNTIME_V2=1`, `oneModelPerConversation=true`) `omc ultragoal` / `omc team` / `omc ask` |
| Cross-Family Adversarial Critic | `https://github.com/Yeachan-Heo/oh-my-codex` (`v0.22.10`) + `https://github.com/max-sixty/worktrunk` | `gpt-6.2-astra` `omx exec` / `omx mission` in isolated git worktrees |
| 8-Slot Lifecycle & Peer Spine | `https://github.com/ComposioHQ/agent-orchestrator` + `https://github.com/aannoo/hcom` + `https://github.com/steveyegge/beads` | 8-slot cross-vendor `AO` convergence, SQLite WAL `peer_bus.db`, `hcom` PTY push & `bd` DAG tracking |
| Typed Python DAGs & 1M Synthesis | `https://github.com/google-antigravity/antigravity-sdk-python` (`v1.5.10`) | `16` `run_workflow` Python DAGs + Native Swarm `workspace:share` |
| Non-GPT Polyglot Graph Runtime | `https://github.com/code-yeongyu/oh-my-openagent` (`v5.1.75`) | `claude-sonnet-5-5` / `deepseek-v4.1-flash` `Hephaestus` (`forbids_gpt_on_hephaestus=true`) |
| Role-Selected Thinking Workers | `https://github.com/can1357/oh-my-pi` (`v18.22.0`) + `https://github.com/block/goose` (`v1.59.2`) | `@worker` explicit `--effort` workers & AAIF MCP recipes |
| Open-Weights Quant Verifier | `https://github.com/native-agent-stack/dsh-sota-harness` (`v0.2.2-rc.2`) | `deepseek-v4.1-flash` (`deepseek-flash`) 10-layer probes & `<= 2026-10-15` pre-wall batch evaluator |

## 2. 18 Immutable `40`-Hex Quantitative & Execution Upstream Shelf Pins (`DF1..DF9`)

- `alpacahq/alpaca-py` @ `c42add7c0a7026e2ead3ed64e76f4def2b99fda4` (`DF1` SIP, `DF2` BOATS / Dec-6 `23/5`)
- `alpacahq/alpaca-mcp-server` @ `63cc4278d87b31f3ed4efcfaa55624095c6d7be8`
- `nautechsystems/nautilus_trader` @ `da6b57aefdd62b44f675e434ffcfefca7f4025dd` (`T1` / `T3B` event simulation)
- `HighwindCapital/nautilus-alpaca` @ `59685d56631b981018a189b5ced1a7000a50bfbd`
- `pola-rs/polars` @ `7f902bd3ffd27ff82d14278a09a295ff2f7aed92` (`DF3` `RAW`-vs-`ALL`, `64`-thread `Noesis-Carbon` lake scans)
- `duckdb/duckdb` @ `d54cbbe3df17e8e5ce68312f483b4155836112aa` (`DF7` FINRA `T-1`)
- `dgunning/edgartools` @ `574c2bd15f6c629bceef03b6550ea8ac8abf3473` (`DF5` SEC `acceptanceDateTime`, `DF6` XBRL float)
- `ml4t/diagnostic` @ `19e76072e64a18c9ba56130e4a7bcc0bc871f57e` (`DSR` / `PBO`)
- `skfolio/skfolio` @ `90e3fb907fab39d244d899f3caf4e9676889309c` (`CombinatorialPurgedCV`)
- `nkaz001/hftbacktest` @ `5f3ec40b2afb764e0fea112f941ed85523ef4e88` (`RiskAdverseQueueModel` `100x` round-lot queue)
- `ib-api-reloaded/ib_async` @ `ab629f34c1823ea4c1542f32f07377208a86bdfd` (`DF9` IBKR `:4002` Paper `L1`)
- `finos/perspective` @ `0264ec13cd28ef4a2a136c8ef021c3c112bc8990`
- `tradingview/lightweight-charts` @ `c29c51e1e5bc61981da5832c97797cb8283d120f`
- `ranaroussi/quantstats` @ `d1a214fb906e76f974f45cdccf923b601c67a756`
- `polakowo/vectorbt` @ `a52a984b631624bb9daf41cb19f532fe559cf0ef`
- `unionai-oss/pandera` @ `02b375ab43f39f8c5c5108695c1791fa04f99a26`
- `gerrymanoim/exchange_calendars` @ `dbe38b1f6887434bbdd1a7d2df6ff8f1742a048a` (`DF4` `XNYS` `RVOL_tod`, `DF8` Rule 4560 `T+8`)
- `statsmodels/statsmodels` @ `278ff9950636cdd4939b4055e339a8e681d79cab` (date-clustered HAC SEs)
