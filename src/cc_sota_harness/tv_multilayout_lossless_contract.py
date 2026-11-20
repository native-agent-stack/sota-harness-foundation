"""Finalized TradingView Library Landscape, 5-Layout Multi-Surface Manifest, Large-Cap 6-14 bps Micro-Trail,
Fast-Sell & Suitable-Timing Re-Entry, and 1,000 RPM Lossless Coordination Contract (`ADR-0045`).

Converges across the dual-machine (`Stationary Noesis <-> Portable Mac M5 Max`) Orca ecosystem:
1. **Advanced TradingView Library Landscape & 4-Class Capability Taxonomy (`sota-tv-library-landscape.v1`):**
   Audits and classifies all 14 TradingView & companion open-source/official charting, Pine v6, screener, and
   execution libraries under `sota-upstream-shelf-lock ADR-0017` (`PINNED_INTEGRATE`,
   `OPTIONAL_READ_ONLY_OR_OFFLINE_RESEARCH`, `PHILOSOPHY_ONLY`, `HARD_REFUSED_EXECUTION_SAAS`).
2. **5-Layout Multi-Surface Coordination Manifest (`sota-tv-multilayout-manifest.v1`):**
   Synchronizes Noesis `DISPLAY2` 120Hz primary (`Layout '3'`), Noesis `DISPLAY1` 4K wall dock, `24/5` Overnight
   `BOATS` + VIX regime layout, OpenBB Workspace + FINOS Perspective + Lightweight Charts v5 cockpit, and Mac M5 Max
   failover (`Layout 'agy'`) with zero table collision (`>= 92%` unobstructed candles) and `order_authority = False`.
3. **Large-Cap Ultra-Minimal `6-14 bps` Micro-Trail & Sub-Venue Synthetic Fast-Sell Guardian:**
   Exact-`Decimal` Reg NMS Rule 612 (`$0.01 >= $1.00`, `$0.0001 < $1.00`, `$1.00`-crossing safe), `ADR-0022 <= 2.00%`
   initial cap, `5-10 bps` instant `BE+` arm, `6-14 bps` dynamic micro-trail width, automatic detection of Alpaca's
   `>= 0.10% + 1 tick` venue floor (`sub_venue_micro_trail_active=True` -> `1.1s` awake synthetic fast-sell with
   green-floor preservation), monotonic ratchet, and uncapped upside (`take_profit_cap_enabled = False`).
4. **Suitable-Timing Post-Trail Fast Re-Entry (`Window A` Pullback/Bounce + `Window B` Tight Coil):**
   Symmetric Long & fee-free ETB/SSR Short Wave-2/3 re-entry with anti-chase ceilings, dwell windows (`6s`/`12s`/`30s`),
   R3a daily scratch breaker, `ADR-0064` strategy quarantine, and `max_waves = 3`.
5. **`1,000 req/min` Alpaca Algo-Plus + `3,000 req/min` IBKR `:4002` + `18 req/min` TV Cloud MCP Rate Firewall:**
   Isolated `>= 10%` protective-exit reserve (including HTTP-429 `200/20` non-starvation), all 6 uncapped quickbar
   presets (`[P][L][M][B][S][O]`, `TP OFF`, whole-share `Shares`), and fail-closed live-port/SaaS refusal.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Any, Literal

TV_LANDSCAPE_CONTRACT_SCHEMA = "sota-tv-multilayout-lossless.v1"
ADR0022_MAX_STOP_PCT_DEC = Decimal("2.00")
ADR0022_MAX_STOP_PCT_FLOAT = 2.00
MIN_PRICE_USD_DEC = Decimal("0.05")
ALPACA_MIN_VENUE_TRAIL_DEC = Decimal("0.0010")  # 0.10% (10 bps) observed broker HTTP-422 floor

LARGECAP_MIN_TRAIL_BPS = 6.0
LARGECAP_MAX_TRAIL_BPS = 14.0
LARGECAP_BE_ARM_MIN_BPS = 5.0
LARGECAP_BE_ARM_MAX_BPS = 10.0
LARGECAP_MAX_SPREAD_BPS = 8.0
LARGECAP_ADV_PRIMARY_USD = 500_000_000.0
LARGECAP_ADV_SECONDARY_USD = 150_000_000.0
LARGECAP_SECONDARY_MAX_ATR_1M_PCT = 0.12

ALPACA_ALGO_PLUS_MAX_RPM = 1000
ALPACA_ALGO_PLUS_EXIT_RESERVE_RPM = 100
ALPACA_HTTP429_FALLBACK_RPM = 200
ALPACA_HTTP429_EXIT_RESERVE_RPM = 20
IBKR_PAPER_PORT = 4002
IBKR_PAPER_MAX_MPM = 3000
IBKR_PAPER_MAX_PER_SEC = 50
IBKR_PAPER_EXIT_RESERVE_MPM = 300
TV_CLOUD_MCP_MAX_RPM = 18

MAX_REENTRY_WAVES = 3
REENTRY_EXPIRY_SEC = 300.0
DAILY_SCRATCH_MAX_LOSS_BPS = 75.0
DAILY_SCRATCH_MAX_CONSECUTIVE = 4
SYMBOL_R3A_MAX_DAILY_STOPOUTS = 2

ALLOWED_PAPER_PORTS: frozenset[int] = frozenset({4002, 7497, 8787, 8797, 8799})
FORBIDDEN_LIVE_PORTS: frozenset[int] = frozenset({4001, 7496, 8796, 8798})
FORBIDDEN_LIVE_HOSTS: frozenset[str] = frozenset({"api.alpaca.markets"})  # hard-refused live-capital endpoint

UNCAPPED_QUICKBAR_CHIPS: tuple[str, ...] = ("P", "L", "M", "B", "S", "O")

QUARANTINED_STRATEGY_IDS_ADR0064: frozenset[str] = frozenset(
    {
        "SOTA_DUAL_CLIMAX_STOP_AND_REVERSE",
        "POST_VIX_REVERSAL",
        "POST_VIX_REVERSAL_MAJOR_GROWTH_THRUST",
        "SOTA_DUAL_EXTREME_BALANCE_BREAK_EARLY",
        "BLIND_WAVE2_REENTRY",
        "RAPID_WAVE2_REENTRY_STRESS",
        "FLOW_VELOCITY_CAPITAL_RECYCLE",
    }
)

ACTIVE_CORE_STRATEGY_IDS_ADR0064: frozenset[str] = frozenset(
    {
        "BJZZ_SUBPENNY_INST_DARK_SWEEP",
        "VIX_SPIKE_AND_CRUSH_REGIME_SURFER",
        "ZARATTINI_2024_5M_ORB",
        "ZARATTINI_2025_NOISE_VWAP",
        "H090_TIGHT_SPREAD_HIGH_OFI_PASSIVE_BID",
        "H01_PRE_TRAVEL_POCKET_PIVOT",
        "H08_FIRST_HAND_CATALYST_IGNITION",
    }
)

HARD_REFUSED_EXECUTION_SAAS_BRIDGES: frozenset[str] = frozenset(
    {
        "signalstack",
        "traderspost",
        "pineconnector",
        "crosstrade",
        "openalgo",
        "marketcalls/openalgo",
        "3commas",
        "alertatron",
    }
)

_TICK_ABOVE_ONE = Decimal("0.01")
_TICK_BELOW_ONE = Decimal("0.0001")
_ONE_DOLLAR = Decimal("1.00")
_HUNDRED = Decimal("100")
_TEN_THOUSAND = Decimal("10000")

# ---------------------------------------------------------------------------
# 1. Finalized Advanced TradingView Library Landscape & 4-Class Stack Matrix
# ---------------------------------------------------------------------------

TV_LIBRARY_LANDSCAPE_STACK: tuple[dict[str, Any], ...] = (
    {
        "library_id": "lightweight-charts",
        "repo_or_vendor": "tradingview/lightweight-charts",
        "url": "https://github.com/tradingview/lightweight-charts",
        "version_or_pin": "v5.3.0 shelf @ c29c51e1e5bc61981da5832c97797cb8283d120f (5.0.8 deployed)",
        "license": "Apache-2.0",
        "capability_class": "PINNED_INTEGRATE",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": (
            "v5 native multi-pane canvas",
            "chart.addSeries(SeriesType, options) modular tree-shaking (~35KB)",
            "29 official plugins (volume-profile, session-highlighting, bands-indicator, user-price-lines, delta-tooltip)",
            "Yield Curve & Options horizontal-price series",
        ),
        "stack_role": "Self-hosted 60fps HTML5 canvas rendering SIP/BOATS bars, VWAP, and ADR-0063 monotonic Chandelier stops",
    },
    {
        "library_id": "perspective",
        "repo_or_vendor": "finos/perspective",
        "url": "https://github.com/finos/perspective",
        "version_or_pin": "v5.9.2 @ 0264ec13cd28ef4a2a136c8ef021c3c112bc8990",
        "license": "Apache-2.0",
        "capability_class": "PINNED_INTEGRATE",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": (
            "WebAssembly typed streaming tables",
            "Sub-millisecond multi-column pivot/filter",
            "ADR-0059 Causal Markout TCA (+1s/+5s/+30s/+60s) blotter",
        ),
        "stack_role": "High-density streaming OMS blotter, DF1..DF12 scanner grid, and TCA attribution view",
    },
    {
        "library_id": "openbb-workspace-backend",
        "repo_or_vendor": "OpenBB-finance/backends-for-openbb",
        "url": "https://github.com/OpenBB-finance/backends-for-openbb",
        "version_or_pin": "main @ a6293707576e16edda8305adda95b07b6a4b968b",
        "license": "MIT",
        "capability_class": "PINNED_INTEGRATE",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": (
            "widgets.json + apps.json custom FastAPI backend protocol",
            "CORS https://pro.openbb.co workspace mounting",
            "Paper-only 24/5 BOATS whole-share collared Limit order stager (live ports refused)",
        ),
        "stack_role": "Primary upstream-first research & staging terminal replacing hand-rolled HTML/static Pine tables",
    },
    {
        "library_id": "nautilus_trader",
        "repo_or_vendor": "nautechsystems/nautilus_trader",
        "url": "https://github.com/nautechsystems/nautilus_trader",
        "version_or_pin": "v2.0.0rc9 @ da6b57aefdd62b44f675e434ffcfefca7f4025dd",
        "license": "LGPL-3.0-or-later",
        "capability_class": "PINNED_INTEGRATE",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": (
            "84 Rust indicators (ER, KAMA, Buy/Sell Pressure, KVO, KC/BB TTM Squeeze, VWAP, SpreadAnalyzer)",
            "Event-driven S1/S2 simulation & OTO/OCO contingency parity",
        ),
        "stack_role": "Deterministic Rust indicator mathematical source-of-truth & Stage-1 simulation parity",
    },
    {
        "library_id": "hftbacktest",
        "repo_or_vendor": "nkaz001/hftbacktest",
        "url": "https://github.com/nkaz001/hftbacktest",
        "version_or_pin": "main @ 5f3ec40b2afb764e0fea112f941ed85523ef4e88",
        "license": "MIT",
        "capability_class": "PINNED_INTEGRATE",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": (
            "RiskAdverseQueueModel passive-bid queue fill replay",
            "Stoikov microprice, L1 queue imbalance & Cont-Kukanov-Stoikov OFI",
        ),
        "stack_role": "Stage-2 nanosecond L1 queue fill parity & passive-bid preset [P] calibration",
    },
    {
        "library_id": "tradingview-official-cloud-mcp",
        "repo_or_vendor": "TradingView Official Cloud MCP",
        "url": "https://mcp.tradingview.com/mcp",
        "version_or_pin": "RFC 9728 OAuth 2.1 PKCE + MCP 2025-03-26 (38 tools, 0 broker-order tools)",
        "license": "Proprietary ToS",
        "capability_class": "OPTIONAL_READ_ONLY_OR_OFFLINE_RESEARCH",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": (
            "mcp-tv-validate-pine-script compiler check",
            "mcp-tv-run-pine-indicator & mcp-tv-run-pine-backtest",
            "mcp-tv-create/update-pine-script & mcp-watchlist-* delta sync (<= 18 calls/min)",
            "Win32 DPAPI / macOS Keychain token storage (0 plaintext secrets)",
        ),
        "stack_role": "Single-writer Cloud Pine compiler/backtest verification & zero-waste delta watchlist sync",
    },
    {
        "library_id": "pine-script-v6-libraries",
        "repo_or_vendor": "TradingView Pine Script v6 Native Runtime",
        "url": "https://www.tradingview.com/pine-script-docs/language/libraries/",
        "version_or_pin": "Pine Script v6 (dynamic_requests, request.footprint, force_overlay, UDTs/enums)",
        "license": "Proprietary ToS",
        "capability_class": "OPTIONAL_READ_ONLY_OR_OFFLINE_RESEARCH",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": (
            "Reusable library() exports with UDTs, methods, enums, and dynamic request.security()",
            "Native request.footprint() (POC, VAH, VAL, volume delta, row imbalances)",
            "force_overlay=true single-script multi-pane projection (>92% unobstructed candles)",
            "Native Pine Screener multi-symbol scans + non-repainting barstate.isconfirmed/lookahead_off",
        ),
        "stack_role": "On-chart visual HUD, Strategy Tester parity & alert-only notification layer (0 broker execution)",
    },
    {
        "library_id": "tradingview-desktop-uia",
        "repo_or_vendor": "TradingView Desktop + vercel-labs/agent-desktop + orca computer",
        "url": "https://github.com/vercel-labs/agent-desktop",
        "version_or_pin": "agent-desktop v1.3.1 (Apache-2.0) + orca-computer-use-windows 1.0.0",
        "license": "Apache-2.0 (driver) / Proprietary (TV Desktop)",
        "capability_class": "OPTIONAL_READ_ONLY_OR_OFFLINE_RESEARCH",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": (
            "Background L2 OS Accessibility (Win32 UIA / macOS AXUIElement) zero-focus-steal inspection",
            "Dual-machine isolated layouts (Noesis Layout '3' autosave OFF vs Mac Layout 'agy' autosave ON)",
            "6 uncapped quickbar presets [P][L][M][B][S][O] (whole shares, TP OFF) auto-adopted post-fill",
        ),
        "stack_role": "Live 24H/BOATS charting lens & human-attended quickbar ticket surface",
    },
    {
        "library_id": "tvscreener",
        "repo_or_vendor": "deepentropy/tvscreener",
        "url": "https://github.com/deepentropy/tvscreener",
        "version_or_pin": "MIT public screener DataFrame + optional MCP client",
        "license": "MIT",
        "capability_class": "OPTIONAL_READ_ONLY_OR_OFFLINE_RESEARCH",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": (
            "Programmatic stock/ETF technical screener queries into DataFrames",
            "Cross-check reference against first-hand DF1..DF12 PIT SIP/BOATS/EDGAR/FINRA scanner",
        ),
        "stack_role": "Optional offline cross-validation screener; never replaces PIT DF1..DF12 primary feeds",
    },
    {
        "library_id": "pynecore",
        "repo_or_vendor": "PyneSys/pynecore",
        "url": "https://github.com/PyneSys/pynecore",
        "version_or_pin": "Apache-2.0 Python Pine-compatible runtime",
        "license": "Apache-2.0",
        "capability_class": "PHILOSOPHY_ONLY",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": (
            "Pine-compatible local Python bar-by-bar execution semantics",
            "Offline indicator parity reference without TradingView cloud dependency",
        ),
        "stack_role": "Philosophy/benchmark reference for local Python-vs-Pine indicator math parity",
    },
    {
        "library_id": "pinets",
        "repo_or_vendor": "LuxAlgo/PineTS",
        "url": "https://github.com/LuxAlgo/PineTS",
        "version_or_pin": "Open-source + dual commercial TS/JS Pine runtime",
        "license": "Dual OSS/Commercial",
        "capability_class": "PHILOSOPHY_ONLY",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": ("TypeScript/Node Pine v5/v6 execution model for browser/Lightweight Charts pipelines",),
        "stack_role": "Design reference only (dual-license boundary excluded from core Python/WASM bundle)",
    },
    {
        "library_id": "lightweight-charts-python",
        "repo_or_vendor": "louisnw01/lightweight-charts-python",
        "url": "https://github.com/louisnw01/lightweight-charts-python",
        "version_or_pin": "MIT Python desktop/notebook wrapper for lightweight-charts",
        "license": "MIT",
        "capability_class": "PHILOSOPHY_ONLY",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": ("Pythonic multipane subchart & marker wiring ergonomics",),
        "stack_role": "Ergonomics reference; production cockpit embeds pinned Apache-2.0 lightweight-charts directly",
    },
    {
        "library_id": "tradingview-advanced-charts-trading-platform",
        "repo_or_vendor": "TradingView Advanced Charts / Trading Platform Broker API",
        "url": "https://www.tradingview.com/HTML5-stock-forex-bitcoin-charting-library/",
        "version_or_pin": "Proprietary Commercial Enterprise License (8-panel sync, DOM, broker_factory)",
        "license": "Commercial Proprietary",
        "capability_class": "PHILOSOPHY_ONLY",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": (
            "Up to 8 synchronized chart panels (symbol/crosshair/interval sync)",
            "On-chart order lines, DOM ladder, and quick-preset bracket geometry",
        ),
        "stack_role": "UX & multi-layout geometry reference only; never bundled without enterprise agreement",
    },
    {
        "library_id": "third-party-tv-webhook-saas-and-openalgo",
        "repo_or_vendor": "marketcalls/openalgo (AGPL-3.0) + SignalStack / TradersPost / PineConnector / CrossTrade",
        "url": "https://github.com/marketcalls/openalgo",
        "version_or_pin": "AGPL-3.0 / Closed SaaS alert-to-broker relays",
        "license": "AGPL-3.0 / Proprietary SaaS",
        "capability_class": "HARD_REFUSED_EXECUTION_SAAS",
        "order_authority": False,
        "visual_may_bind_webhook": False,
        "capabilities": ("Third-party webhook-to-broker order relays (hard-refused by ADR-0017 in paper and live)",),
        "stack_role": "HARD-REFUSED: zero external SaaS or AGPL relay may hold broker keys or dispatch orders",
    },
)

# ---------------------------------------------------------------------------
# 2. Finalized 5-Layout Multi-Surface Coordination Manifest
# ---------------------------------------------------------------------------

CANONICAL_TV_MULTI_LAYOUTS: tuple[dict[str, Any], ...] = (
    {
        "layout_id": "L1_NOESIS_PRIMARY_LARGECAP_MICROTRAIL",
        "display_surface": "Noesis DISPLAY2 (120Hz Primary Work Monitor — Zero Focus Steal)",
        "host_role": "stationary_noesis_win32",
        "tv_cloud_layout_name": "3",
        "autosave_enabled": False,
        "pane_grid": "2-pane synced (1m Microstructure + 5m ORB/VWAP, 24H/BOATS:)",
        "unobstructed_candle_area_min_pct": 92.0,
        "hud_anchors": {
            "bottom_left": "SOTA v1.0 Live Lossless HUD (6-14 bps Large-Cap Micro-Trail + Wave-2 Timer)",
            "bottom_right": "SOTA Live Ranker & Preset HUD (<=16 request.security calls, live [P]/[L]/[M]/[B]/[S]/[O])",
            "top_right": "SOTA Master Strategy Self-Audit HUD (showBoard=false)",
            "lower_pane": "TradingView Built-in Volume delta (or Pine v6 request.footprint POC/Delta)",
        },
        "primary_presets": ("S", "P", "L"),
        "target_strategies": (
            "BJZZ_SUBPENNY_INST_DARK_SWEEP",
            "ZARATTINI_2025_NOISE_VWAP",
            "H090_TIGHT_SPREAD_HIGH_OFI_PASSIVE_BID",
        ),
        "lossless_engine_binding": {
            "paper_lanes": ("P1:8799", "P2:8787", "P3:8797", "P4:4002"),
            "trail_band_bps": (LARGECAP_MIN_TRAIL_BPS, LARGECAP_MAX_TRAIL_BPS),
            "be_arm_band_bps": (LARGECAP_BE_ARM_MIN_BPS, LARGECAP_BE_ARM_MAX_BPS),
            "sub_venue_synthetic_fast_sell_sec": 1.1,
            "rate_budget_rpm": ALPACA_ALGO_PLUS_MAX_RPM,
            "exit_reserve_rpm": ALPACA_ALGO_PLUS_EXIT_RESERVE_RPM,
        },
        "order_authority": False,
    },
    {
        "layout_id": "L2_NOESIS_4K_WALL_EXTREME_MOVER_EP",
        "display_surface": "Noesis DISPLAY1 (4K Companion Wall Dock)",
        "host_role": "stationary_noesis_win32",
        "tv_cloud_layout_name": "3-Wall-4K",
        "autosave_enabled": False,
        "pane_grid": "4-chart synced grid (1m Ignition + 5m ORB + 15m Structure + Daily VCP/EP)",
        "unobstructed_candle_area_min_pct": 92.0,
        "hud_anchors": {
            "bottom_left": "SOTA Master All-In-One 24/5 Indicator (Nautilus ER/KAMA/Pressure/KVO/TTM + VWAP)",
            "bottom_right": "SOTA Live Ranker (Early Shock, VDU Coil, SEC <=15m 8-K EP)",
            "top_right": "Strategy Tester Parity Overlay (showBoard=false)",
            "lower_pane": "Built-in Volume delta",
        },
        "primary_presets": ("O", "B", "M"),
        "target_strategies": (
            "ZARATTINI_2024_5M_ORB",
            "H01_PRE_TRAVEL_POCKET_PIVOT",
            "H08_FIRST_HAND_CATALYST_IGNITION",
        ),
        "lossless_engine_binding": {
            "paper_lanes": ("P2:8787", "P3:8797", "P4:4002"),
            "initial_stop_cap_pct": ADR0022_MAX_STOP_PCT_FLOAT,
            "core_harvest_50_50_uncapped": True,
            "chandelier_mfe_tiers_pct": (65, 75, 82, 86),
            "rate_budget_rpm": ALPACA_ALGO_PLUS_MAX_RPM,
            "exit_reserve_rpm": ALPACA_ALGO_PLUS_EXIT_RESERVE_RPM,
        },
        "order_authority": False,
    },
    {
        "layout_id": "L3_24X5_OVERNIGHT_BOATS_VIX_MACRO",
        "display_surface": "Noesis 24/5 Overnight BOATS & Macro Volatility Dock",
        "host_role": "stationary_noesis_win32",
        "tv_cloud_layout_name": "3-BOATS-24x5",
        "autosave_enabled": False,
        "pane_grid": "3-chart synced (BOATS: Active Leader + UVXY/SVIX VIX Proxy + SPY/QQQ 20:00-ET VWAP)",
        "unobstructed_candle_area_min_pct": 92.0,
        "hud_anchors": {
            "bottom_left": "24/5 BOATS Session Highlight + Monotonic Spread/Quote Age Strip",
            "bottom_right": "SOTA Live Ranker (07 Overnight BOATS + VIX Regime)",
            "top_right": "Dec-6 2026 23/5 SIP Cutover Mode Indicator",
            "lower_pane": "Built-in Volume delta",
        },
        "primary_presets": ("L", "P"),
        "target_strategies": (
            "VIX_SPIKE_AND_CRUSH_REGIME_SURFER",
            "BJZZ_SUBPENNY_INST_DARK_SWEEP",
        ),
        "lossless_engine_binding": {
            "paper_lanes": ("P1:8799", "P2:8787", "P4:4002"),
            "boats_max_spread_bps": 35.0,
            "boats_awake_guardian_sec": 1.1,
            "ibkr_overnight_exchange": "OVERNIGHT",
            "dec6_23x5_sip_ready": True,
        },
        "order_authority": False,
    },
    {
        "layout_id": "L4_OPENBB_PERSPECTIVE_LWC_COCKPIT",
        "display_surface": "Self-Hosted OpenBB Workspace + FINOS Perspective WASM + Lightweight Charts v5",
        "host_role": "stationary_noesis_win32",
        "tv_cloud_layout_name": "OPENBB_WASM_COCKPIT",
        "autosave_enabled": True,
        "pane_grid": "Multi-widget workspace (DF1..DF12 Targets + LWC v5 Multi-Pane + ADR-0059 TCA + 24/5 Paper Stager)",
        "unobstructed_candle_area_min_pct": 92.0,
        "hud_anchors": {
            "top_panel": "DF1..DF12 Active Market Targets & ADR-0064 Quarantine Status",
            "center_canvas": "Lightweight Charts v5 Multi-Pane (Candles + VWAP + Chandelier Stop + Volume Profile)",
            "bottom_blotter": "FINOS Perspective v5.9.2 WASM OMS Blotter & +1s/+5s/+30s/+60s Causal Markout TCA",
            "side_stager": "Paper-Only 24/5 BOATS Collared Limit Stager (Live Ports 4001/7496/8796/8798 Hard-Refused)",
        },
        "primary_presets": ("P", "L", "M", "B", "S", "O"),
        "target_strategies": tuple(sorted(ACTIVE_CORE_STRATEGY_IDS_ADR0064)),
        "lossless_engine_binding": {
            "paper_lanes": ("P1:8799", "P2:8787", "P3:8797", "P4:4002"),
            "openbb_widgets_endpoint": "/api/openbb/widgets.json",
            "rate_budget_rpm": ALPACA_ALGO_PLUS_MAX_RPM,
            "ibkr_overflow_mpm": IBKR_PAPER_MAX_MPM,
        },
        "order_authority": False,
    },
    {
        "layout_id": "L5_PORTABLE_MAC_M5_MAX_FAILOVER",
        "display_surface": "Apple M5 Max Portable Command Cockpit & Explicit Hot Failover",
        "host_role": "portable_mac_m5_max",
        "tv_cloud_layout_name": "agy",
        "autosave_enabled": True,
        "pane_grid": "2-pane mirror (1m + 5m synced) + Read-Only :8792 WireGuard Telemetry",
        "unobstructed_candle_area_min_pct": 92.0,
        "hud_anchors": {
            "bottom_left": "SOTA v1.0 Live Lossless HUD",
            "bottom_right": "SOTA Live Ranker & Preset HUD",
            "top_right": "Single-Writer Cloud MCP Delta Sync Status (<= 18 calls/min)",
            "lower_pane": "Built-in Volume delta",
        },
        "primary_presets": ("P", "L", "M", "B", "S", "O"),
        "target_strategies": tuple(sorted(ACTIVE_CORE_STRATEGY_IDS_ADR0064)),
        "lossless_engine_binding": {
            "single_active_broker_host_only": True,
            "primary_sovereign_host": "stationary_noesis_win32",
            "mac_default_mode": "READ_ONLY_COCKPIT_AND_SINGLE_WRITER_CLOUD_SYNC",
            "tv_cloud_mcp_max_rpm": TV_CLOUD_MCP_MAX_RPM,
        },
        "order_authority": False,
    },
)

# ---------------------------------------------------------------------------
# 3. Exact-Decimal Rule-612 Helpers & Large-Cap 6-14 bps Micro-Trail Engine
# ---------------------------------------------------------------------------


def _to_strict_decimal(value: float | int | Decimal | str, name: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{name} must be a finite number (got {value!r})")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f"{name} must be finite (got {value!r})")
        return value
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise ValueError(f"{name} must be finite (got {value!r})")
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            d = Decimal(value.strip())
        except InvalidOperation as exc:
            raise ValueError(f"{name} is not a valid decimal (got {value!r})") from exc
        if not d.is_finite():
            raise ValueError(f"{name} must be finite (got {value!r})")
        return d
    raise ValueError(f"{name} must be numeric (got {type(value).__name__})")


def _normalize_side(side: str) -> Literal["long", "short"]:
    s = str(side or "").strip().lower()
    if s in ("long", "buy"):
        return "long"
    if s in ("short", "sell"):
        return "short"
    raise ValueError(f"Unsupported side {side!r}; expected long/buy or short/sell")


def rule612_tick_for_price(price_px: Decimal) -> Decimal:
    return _TICK_ABOVE_ONE if price_px >= _ONE_DOLLAR else _TICK_BELOW_ONE


def quantize_rule612_price(price_px: float | int | Decimal | str, *, rounding: str = ROUND_FLOOR) -> Decimal:
    """Exact Reg NMS Rule 612 quantization (`$0.01 >= $1.00`, `$0.0001 < $1.00`, `$1.00`-crossing safe)."""
    d = _to_strict_decimal(price_px, "price_px")
    if d <= Decimal("0"):
        raise ValueError(f"price_px must be > 0 (got {price_px!r})")
    tick = rule612_tick_for_price(d)
    q = (d / tick).to_integral_value(rounding=rounding) * tick
    if q < _ONE_DOLLAR and d >= _ONE_DOLLAR and rounding == ROUND_CEILING:
        q = _ONE_DOLLAR
    if q <= Decimal("0"):
        q = _TICK_BELOW_ONE
    return q.quantize(rule612_tick_for_price(q))


def venue_min_trail_bps(ref_px: float | int | Decimal | str) -> float:
    """Alpaca native trailing_stop minimum accepted width in bps (`>= 10 bps + 1 Rule-612 tick`, capped at 200 bps)."""
    d_px = _to_strict_decimal(ref_px, "ref_px")
    if d_px < MIN_PRICE_USD_DEC:
        raise ValueError(f"ref_px must be >= ${MIN_PRICE_USD_DEC} (got {d_px})")
    tick = rule612_tick_for_price(d_px)
    min_dollars = (d_px * ALPACA_MIN_VENUE_TRAIL_DEC).quantize(tick, rounding=ROUND_CEILING) + tick
    bps = float((min_dollars / d_px) * _TEN_THOUSAND)
    return round(min(200.0, max(10.0, bps)), 4)


def classify_cap_liquidity_tier(
    *,
    adv_20d_usd: float,
    atr_1m_pct: float,
    spread_bps: float,
) -> Literal["MEGA_LARGE_CAP", "LIQUID_MID_CAP", "EXTREME_MOVER"]:
    d_adv = float(_to_strict_decimal(adv_20d_usd, "adv_20d_usd"))
    d_atr = float(_to_strict_decimal(atr_1m_pct, "atr_1m_pct"))
    d_spr = float(_to_strict_decimal(spread_bps, "spread_bps"))
    if d_adv < 0.0 or d_atr <= 0.0 or d_spr <= 0.0:
        raise ValueError("adv_20d_usd >= 0, atr_1m_pct > 0, and spread_bps > 0 required")
    if d_spr <= LARGECAP_MAX_SPREAD_BPS and (
        d_adv >= LARGECAP_ADV_PRIMARY_USD
        or (d_adv >= LARGECAP_ADV_SECONDARY_USD and d_atr <= LARGECAP_SECONDARY_MAX_ATR_1M_PCT)
    ):
        return "MEGA_LARGE_CAP"
    if d_adv >= 50_000_000.0 and d_atr <= 0.50 and d_spr <= 20.0:
        return "LIQUID_MID_CAP"
    return "EXTREME_MOVER"


@dataclass(frozen=True, slots=True)
class LargeCapMicroTrailPlan:
    side: Literal["long", "short"]
    liquidity_tier: Literal["MEGA_LARGE_CAP", "LIQUID_MID_CAP", "EXTREME_MOVER"]
    phase: str
    entry_px: Decimal
    extreme_px: Decimal
    current_px: Decimal
    mfe_bps: float
    be_arm_bps: float
    be_lock_bps: float
    gain_lock_armed: bool
    target_trail_bps: float
    native_broker_trail_bps: float
    sub_venue_micro_trail_active: bool
    active_stop_px: Decimal
    realized_risk_from_entry_bps: float
    locked_gain_bps: float
    fast_sell_triggered: bool
    fast_sell_limit_px: Decimal | None
    fast_sell_sweep_bps: float
    take_profit_cap_enabled: bool = False
    awake_guardian_interval_sec: float = 1.1

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for key in ("entry_px", "extreme_px", "current_px", "active_stop_px", "fast_sell_limit_px"):
            if d[key] is not None:
                d[key] = float(d[key])
        return d


def compute_largecap_micro_trail_plan(
    *,
    entry_px: float | int | Decimal | str,
    current_px: float | int | Decimal | str,
    extreme_px: float | int | Decimal | str,
    prev_stop_px: float | int | Decimal | str | None = None,
    side: str = "long",
    adv_20d_usd: float = 1_000_000_000.0,
    atr_1m_pct: float = 0.08,
    spread_bps: float = 2.0,
    ofi_pct: float = 0.0,
    position_leverage_x: float = 1.0,
    max_initial_stop_pct: float = 1.25,
    exit_attempt_num: int = 0,
) -> LargeCapMicroTrailPlan:
    """Exact-Decimal Large-Cap Ultra-Minimal `6-14 bps` Micro-Trail & Fast-Sell Planner (`ADR-0045` / `ADR-0022`).

    Invariants:
    - Exact Reg NMS Rule 612 quantization (`$1.00`-crossing safe); strictly finite inputs (`bool`/`NaN`/`Inf` rejected).
    - Initial stop strictly bounded `0 < stop_pct <= min(effective_leverage_cap, 2.00%)`.
    - For `MEGA_LARGE_CAP`: `5-10 bps` instant `BE+` arm, `6-14 bps` dynamic micro-trail width, automatic detection of
      Alpaca's `>= 10 bps + 1 tick` native venue floor (`sub_venue_micro_trail_active=True` -> `1.1s` awake synthetic
      fast-sell marketable limit), green-floor preservation on attempts `0..2`, and strict monotonicity against
      `prev_stop_px`.
    - Zero fixed take-profit upside cap (`take_profit_cap_enabled = False`).
    """
    norm_side = _normalize_side(side)
    is_short = norm_side == "short"

    d_entry = _to_strict_decimal(entry_px, "entry_px")
    d_curr = _to_strict_decimal(current_px, "current_px")
    d_ext = _to_strict_decimal(extreme_px, "extreme_px")
    d_lev = _to_strict_decimal(position_leverage_x, "position_leverage_x")
    d_req_stop_pct = _to_strict_decimal(max_initial_stop_pct, "max_initial_stop_pct")
    spr_bps = float(_to_strict_decimal(spread_bps, "spread_bps"))
    atr_pct = float(_to_strict_decimal(atr_1m_pct, "atr_1m_pct"))
    ofi_f = float(_to_strict_decimal(ofi_pct, "ofi_pct"))

    if isinstance(exit_attempt_num, bool) or not isinstance(exit_attempt_num, int) or exit_attempt_num < 0:
        raise ValueError(f"exit_attempt_num must be int >= 0 (got {exit_attempt_num!r})")
    if d_entry < MIN_PRICE_USD_DEC or d_curr <= Decimal("0") or d_ext <= Decimal("0"):
        raise ValueError("entry_px must be >= $0.05 and current_px / extreme_px must be > 0")
    if d_lev < Decimal("0") or d_lev > Decimal("4"):
        raise ValueError(f"position_leverage_x must be in [0.0, 4.0] (got {d_lev})")
    if d_req_stop_pct <= Decimal("0") or d_req_stop_pct > ADR0022_MAX_STOP_PCT_DEC:
        raise ValueError(f"ADR-0022 violation: max_initial_stop_pct={d_req_stop_pct}% outside (0, 2.00]%")
    if spr_bps <= 0.0 or spr_bps > 250.0 or atr_pct <= 0.0 or atr_pct > 25.0:
        raise ValueError(f"Invalid spread_bps={spr_bps} or atr_1m_pct={atr_pct}")

    # Enforce directional extreme monotonicity relative to entry & current
    if is_short:
        d_extreme = min(d_entry, d_curr, d_ext)
        mfe_dec_bps = ((d_entry - d_extreme) / d_entry) * _TEN_THOUSAND
    else:
        d_extreme = max(d_entry, d_curr, d_ext)
        mfe_dec_bps = ((d_extreme - d_entry) / d_entry) * _TEN_THOUSAND
    mfe_bps = round(float(mfe_dec_bps), 4)

    tier = classify_cap_liquidity_tier(adv_20d_usd=adv_20d_usd, atr_1m_pct=atr_pct, spread_bps=spr_bps)
    atr_1m_bps = atr_pct * 100.0

    # Leverage-aware initial stop cap (ADR-0063 / ADR-0022 — never widens caller's explicit stop cap)
    d_eff_init_pct = min(ADR0022_MAX_STOP_PCT_DEC, d_req_stop_pct)
    if d_lev > Decimal("1"):
        d_lev_cap = (Decimal("1.35") / d_lev).quantize(Decimal("0.0001"), rounding=ROUND_FLOOR)
        d_eff_init_pct = min(d_eff_init_pct, d_lev_cap)

    # Quantize initial hard stop strictly within d_eff_init_pct <= 2.00%
    q_entry = quantize_rule612_price(d_entry, rounding=ROUND_HALF_EVEN)
    if q_entry < MIN_PRICE_USD_DEC:
        q_entry = MIN_PRICE_USD_DEC
    init_ratio = d_eff_init_pct / _HUNDRED
    if is_short:
        anchor_init = min(d_entry, q_entry)
        hard_stop_px = quantize_rule612_price(anchor_init * (Decimal("1") + init_ratio), rounding=ROUND_FLOOR)
        if hard_stop_px <= q_entry:
            step = _TICK_ABOVE_ONE if q_entry >= _ONE_DOLLAR else _TICK_BELOW_ONE
            hard_stop_px = (q_entry + step).quantize(rule612_tick_for_price(q_entry + step))
    else:
        anchor_init = max(d_entry, q_entry)
        hard_stop_px = quantize_rule612_price(anchor_init * (Decimal("1") - init_ratio), rounding=ROUND_CEILING)
        if hard_stop_px >= q_entry:
            step = _TICK_ABOVE_ONE if q_entry > _ONE_DOLLAR else _TICK_BELOW_ONE
            hard_stop_px = (q_entry - step).quantize(rule612_tick_for_price(q_entry - step))

    init_realized_pct = (abs(d_entry - hard_stop_px) / d_entry) * _HUNDRED
    init_realized_q_pct = (abs(q_entry - hard_stop_px) / q_entry) * _HUNDRED
    if (
        init_realized_pct <= Decimal("0")
        or init_realized_q_pct <= Decimal("0")
        or init_realized_pct > d_eff_init_pct
        or init_realized_q_pct > d_eff_init_pct
        or init_realized_pct > ADR0022_MAX_STOP_PCT_DEC
        or init_realized_q_pct > ADR0022_MAX_STOP_PCT_DEC
    ):
        raise ValueError(
            f"Rule 612 initial stop exceeded effective cap {float(d_eff_init_pct):.4f}%: "
            f"raw={float(init_realized_pct):.4f}%, q={float(init_realized_q_pct):.4f}%"
        )

    adverse_flow = (ofi_f >= 6.0) if is_short else (ofi_f <= -6.0)

    if tier == "MEGA_LARGE_CAP":
        be_arm_bps = round(min(LARGECAP_BE_ARM_MAX_BPS, max(LARGECAP_BE_ARM_MIN_BPS, 2.0 * spr_bps + 1.0)), 4)
        be_lock_bps = round(min(4.0, max(2.0, 0.50 * be_arm_bps)), 4)
        gain_lock_armed = mfe_bps >= be_arm_bps
        if mfe_bps >= 50.0 or (gain_lock_armed and adverse_flow):
            target_trail_bps = round(
                min(10.0, max(LARGECAP_MIN_TRAIL_BPS, 1.4 * spr_bps + 0.40 * atr_1m_bps)),
                4,
            )
            phase = "PHASE2_LARGECAP_CLIMAX_MICRO_LOCK"
        elif gain_lock_armed:
            target_trail_bps = round(
                min(12.0, max(7.0, 1.8 * spr_bps + 0.55 * atr_1m_bps)),
                4,
            )
            phase = "PHASE1_LARGECAP_ARMED_MICRO_RUNNER"
        else:
            target_trail_bps = round(
                min(LARGECAP_MAX_TRAIL_BPS, max(8.0, 2.2 * spr_bps + 0.80 * atr_1m_bps)),
                4,
            )
            phase = "PHASE0_LARGECAP_TICK1_MICRO_TRAIL"

        # Progressive retention schedule for MEGA_LARGE_CAP
        if mfe_bps >= 120.0:
            retention_ratio = 0.90
        elif mfe_bps >= 90.0:
            retention_ratio = 0.88
        elif mfe_bps >= 50.0:
            retention_ratio = 0.82
        elif mfe_bps >= 35.0:
            retention_ratio = 0.72
        elif mfe_bps >= 20.0:
            retention_ratio = 0.60
        elif mfe_bps >= 10.0:
            retention_ratio = 0.45
        else:
            retention_ratio = 0.0
        if adverse_flow and gain_lock_armed:
            retention_ratio = min(0.90, max(retention_ratio, 0.60) + 0.12)
    elif tier == "LIQUID_MID_CAP":
        be_arm_bps = round(min(30.0, max(14.0, 2.2 * spr_bps + 6.0)), 4)
        be_lock_bps = round(min(8.0, max(4.0, 0.35 * be_arm_bps)), 4)
        gain_lock_armed = mfe_bps >= be_arm_bps
        if mfe_bps >= 120.0 or (gain_lock_armed and adverse_flow):
            target_trail_bps = round(min(42.0, max(18.0, 0.72 * max(atr_1m_bps, 18.0) + 0.80 * spr_bps)), 4)
            phase = "PHASE2_MIDCAP_CLIMAX_LOCK"
        elif gain_lock_armed:
            target_trail_bps = round(min(58.0, max(28.0, 0.98 * max(atr_1m_bps, 22.0) + 1.00 * spr_bps)), 4)
            phase = "PHASE1_MIDCAP_RUNNER_TRAIL"
        else:
            target_trail_bps = round(min(75.0, max(36.0, 1.22 * max(atr_1m_bps, 24.0) + 1.20 * spr_bps)), 4)
            phase = "PHASE0_MIDCAP_TICK1_TRAIL"
        retention_ratio = (
            0.84 if mfe_bps >= 200.0 else (0.72 if mfe_bps >= 80.0 else (0.58 if mfe_bps >= 30.0 else 0.0))
        )
    else:
        be_arm_bps = round(min(65.0, max(30.0, 1.8 * spr_bps)), 4)
        be_lock_bps = round(min(12.0, max(6.0, 0.25 * be_arm_bps)), 4)
        gain_lock_armed = mfe_bps >= be_arm_bps
        eff_noise_bps = max(atr_1m_bps, 42.0) + 1.5 * min(45.0, spr_bps)
        if mfe_bps >= 200.0 or (gain_lock_armed and adverse_flow):
            target_trail_bps = round(min(135.0, max(85.0, 0.90 * eff_noise_bps)), 4)
            phase = "PHASE2_MOVER_CLIMAX_LOCK"
        elif gain_lock_armed:
            target_trail_bps = round(min(180.0, max(105.0, 1.22 * eff_noise_bps)), 4)
            phase = "PHASE1_MOVER_RUNNER_TRAIL"
        else:
            target_trail_bps = round(min(200.0, max(85.0, 1.52 * eff_noise_bps)), 4)
            phase = "PHASE0_MOVER_TICK1_TRAIL"
        retention_ratio = (
            0.86
            if mfe_bps >= 450.0
            else (0.82 if mfe_bps >= 250.0 else (0.75 if mfe_bps >= 125.0 else (0.65 if mfe_bps >= 60.0 else 0.0)))
        )

    # Preserve strict [6.0, 14.0] bps band for MEGA_LARGE_CAP (hard_stop_px enforces tighter initial cap separately)
    eff_init_bps = float(d_eff_init_pct * _HUNDRED)
    if tier != "MEGA_LARGE_CAP":
        target_trail_bps = round(min(target_trail_bps, eff_init_bps, 200.0), 4)

    v_min_bps = venue_min_trail_bps(max(d_extreme, MIN_PRICE_USD_DEC))
    sub_venue_active = target_trail_bps < v_min_bps
    native_broker_trail_bps = round(min(200.0, max(v_min_bps, target_trail_bps)), 4)

    # Compute candidate stop price from trail + breakeven + progressive retention (Rule-612 >=1 tick safe)
    trail_ratio = Decimal(str(target_trail_bps)) / _TEN_THOUSAND
    d_prev: Decimal | None = None
    if prev_stop_px is not None:
        d_prev = quantize_rule612_price(
            _to_strict_decimal(prev_stop_px, "prev_stop_px"),
            rounding=ROUND_FLOOR if is_short else ROUND_CEILING,
        )

    raw_be_armed = gain_lock_armed
    if is_short:
        trail_stop_px = quantize_rule612_price(d_extreme * (Decimal("1") + trail_ratio), rounding=ROUND_CEILING)
        if trail_stop_px <= d_extreme:
            step = _TICK_ABOVE_ONE if d_extreme >= _ONE_DOLLAR else _TICK_BELOW_ONE
            trail_stop_px = quantize_rule612_price(d_extreme + step, rounding=ROUND_CEILING)
        cand_stop = min(hard_stop_px, trail_stop_px)
        be_px = quantize_rule612_price(
            d_entry * (Decimal("1") - Decimal(str(be_lock_bps)) / _TEN_THOUSAND),
            rounding=ROUND_FLOOR,
        )
        q_entry_be = quantize_rule612_price(d_entry, rounding=ROUND_FLOOR)
        if be_px > q_entry_be:
            be_px = q_entry_be
        gain_lock_armed = bool(raw_be_armed and d_extreme < be_px <= d_entry)
        if raw_be_armed and not gain_lock_armed:
            phase = "UNARMED_SUBTICK"
        if gain_lock_armed:
            cand_stop = min(cand_stop, be_px)
            if retention_ratio > 0.0:
                ret_px = quantize_rule612_price(
                    d_entry - (d_entry - d_extreme) * Decimal(str(retention_ratio)),
                    rounding=ROUND_FLOOR,
                )
                if d_extreme < ret_px <= d_entry:
                    cand_stop = min(cand_stop, ret_px)
        if cand_stop < d_extreme:
            cand_stop = quantize_rule612_price(d_extreme, rounding=ROUND_CEILING)
        active_stop_px = min(d_prev, cand_stop) if d_prev is not None else cand_stop
        if active_stop_px > hard_stop_px and d_prev is None:
            active_stop_px = hard_stop_px
        locked_gain_bps = round(float(((d_entry - active_stop_px) / d_entry) * _TEN_THOUSAND), 4)
        risk_from_entry_bps = round(max(0.0, float(((active_stop_px - d_entry) / d_entry) * _TEN_THOUSAND)), 4)
        fast_sell_triggered = d_curr >= active_stop_px
    else:
        trail_stop_px = quantize_rule612_price(d_extreme * (Decimal("1") - trail_ratio), rounding=ROUND_FLOOR)
        if trail_stop_px >= d_extreme:
            step = _TICK_ABOVE_ONE if d_extreme > _ONE_DOLLAR else _TICK_BELOW_ONE
            trail_stop_px = quantize_rule612_price(max(_TICK_BELOW_ONE, d_extreme - step), rounding=ROUND_FLOOR)
        cand_stop = max(hard_stop_px, trail_stop_px)
        be_px = quantize_rule612_price(
            d_entry * (Decimal("1") + Decimal(str(be_lock_bps)) / _TEN_THOUSAND),
            rounding=ROUND_CEILING,
        )
        q_entry_be = quantize_rule612_price(d_entry, rounding=ROUND_CEILING)
        if be_px < q_entry_be:
            be_px = q_entry_be
        gain_lock_armed = bool(raw_be_armed and d_entry <= be_px < d_extreme)
        if raw_be_armed and not gain_lock_armed:
            phase = "UNARMED_SUBTICK"
        if gain_lock_armed:
            cand_stop = max(cand_stop, be_px)
            if retention_ratio > 0.0:
                ret_px = quantize_rule612_price(
                    d_entry + (d_extreme - d_entry) * Decimal(str(retention_ratio)),
                    rounding=ROUND_CEILING,
                )
                if d_entry <= ret_px < d_extreme:
                    cand_stop = max(cand_stop, ret_px)
        if cand_stop > d_extreme:
            cand_stop = quantize_rule612_price(d_extreme, rounding=ROUND_FLOOR)
        active_stop_px = max(d_prev, cand_stop) if d_prev is not None else cand_stop
        if active_stop_px < hard_stop_px and d_prev is None:
            active_stop_px = hard_stop_px
        locked_gain_bps = round(float(((active_stop_px - d_entry) / d_entry) * _TEN_THOUSAND), 4)
        risk_from_entry_bps = round(max(0.0, float(((d_entry - active_stop_px) / d_entry) * _TEN_THOUSAND)), 4)
        fast_sell_triggered = d_curr <= active_stop_px

    # Compute marketable fast-sell exit limit with NBBO-aware green-floor preservation strictly on attempt 0
    fast_sell_sweep_bps = (
        round(min(14.0, max(6.0, 0.50 * spr_bps)), 4)
        if exit_attempt_num == 0
        else round(min(65.0, 22.0 + 20.0 * min(exit_attempt_num, 2)), 4)
    )
    fast_sell_limit_px: Decimal | None = None
    if fast_sell_triggered:
        sw_ratio = Decimal(str(fast_sell_sweep_bps)) / _TEN_THOUSAND
        half_spr_ratio = Decimal(str(0.5 * spr_bps)) / _TEN_THOUSAND
        if is_short:
            raw_lim = d_curr * (Decimal("1") + sw_ratio)
            lim_px = quantize_rule612_price(raw_lim, rounding=ROUND_CEILING)
            est_ask = d_curr * (Decimal("1") + half_spr_ratio)
            if gain_lock_armed and exit_attempt_num == 0 and est_ask <= d_entry * Decimal("0.9996"):
                green_ceil = quantize_rule612_price(d_entry * Decimal("0.9996"), rounding=ROUND_FLOOR)
                if green_ceil >= est_ask:
                    lim_px = min(lim_px, green_ceil)
            fast_sell_limit_px = lim_px
        else:
            raw_lim = max(_TICK_BELOW_ONE, d_curr * (Decimal("1") - sw_ratio))
            lim_px = quantize_rule612_price(raw_lim, rounding=ROUND_FLOOR)
            q_curr_floor = quantize_rule612_price(max(_TICK_BELOW_ONE, d_curr), rounding=ROUND_FLOOR)
            if lim_px > q_curr_floor:
                lim_px = q_curr_floor
            est_bid = d_curr * (Decimal("1") - half_spr_ratio)
            if gain_lock_armed and exit_attempt_num == 0 and est_bid >= d_entry * Decimal("1.0004"):
                green_floor = quantize_rule612_price(d_entry * Decimal("1.0004"), rounding=ROUND_CEILING)
                if green_floor <= est_bid:
                    lim_px = max(lim_px, green_floor)
            fast_sell_limit_px = lim_px

    return LargeCapMicroTrailPlan(
        side=norm_side,
        liquidity_tier=tier,
        phase=phase,
        entry_px=q_entry,
        extreme_px=d_extreme,
        current_px=d_curr,
        mfe_bps=mfe_bps,
        be_arm_bps=be_arm_bps,
        be_lock_bps=be_lock_bps,
        gain_lock_armed=gain_lock_armed,
        target_trail_bps=target_trail_bps,
        native_broker_trail_bps=native_broker_trail_bps,
        sub_venue_micro_trail_active=sub_venue_active,
        active_stop_px=active_stop_px,
        realized_risk_from_entry_bps=risk_from_entry_bps,
        locked_gain_bps=locked_gain_bps,
        fast_sell_triggered=fast_sell_triggered,
        fast_sell_limit_px=fast_sell_limit_px,
        fast_sell_sweep_bps=fast_sell_sweep_bps,
        take_profit_cap_enabled=False,
        awake_guardian_interval_sec=1.1,
    )


# ---------------------------------------------------------------------------
# 4. Suitable-Timing Fast Re-Entry Gate (Window A Pullback + Window B Coil)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReentryTimingDecision:
    approved: bool
    expired: bool
    window: Literal[
        "WINDOW_A_PULLBACK_ABSORPTION",
        "WINDOW_A_BOUNCE_REJECTION",
        "WINDOW_B_TIGHT_COIL_CONTINUATION",
        "WAITING",
        "NONE",
    ]
    reason: str
    side: Literal["long", "short"]
    wave_num: int
    recommended_preset_chip: str | None
    retrace_bps: float
    min_required_dwell_sec: float


def evaluate_suitable_timing_reentry(
    *,
    strategy_id: str,
    exit_px: float,
    live_px: float,
    vwap_px: float,
    retrace_extreme_px: float,
    elapsed_sec: float,
    ofi_pct: float,
    spread_bps: float,
    max_spread_bps: float = 25.0,
    wave_num: int = 2,
    trail_ended: bool = True,
    side: str = "long",
    is_mega_large_cap: bool = True,
    symbol_daily_stopouts: int = 0,
    account_consecutive_scratches: int = 0,
    account_daily_realized_bps: float = 0.0,
    dilution_blocked: bool = False,
    easy_to_borrow: bool = False,
    shortable: bool = False,
    ssr_uptick_compliant: bool = False,
    enforce_adr0064_quarantine: bool = True,
) -> ReentryTimingDecision:
    """Deterministic post-trail lossless fast re-entry timing gate (`Window A` pullback/bounce vs `Window B` tight coil).

    Prevents whipsaw churn & top/bottom-chasing while enabling fast re-entry on clean pullbacks or tight coils:
    - Enforces `ADR-0064` strategy quarantine + active-core allowlist, `DF5` 90-day dilution block, `max_waves <= 3`,
      `<= 300s` expiry, `R3a` 2-stopout lock, and `-75 bps` / `4`-scratch daily circuit breaker.
    - For `side="short"`, fails closed unless caller explicitly confirms `$0 ETB` + `shortable=True` + `SSR uptick`.
    """
    norm_side = _normalize_side(side)
    is_short = norm_side == "short"
    sid = str(strategy_id or "").strip().upper()

    def _deny(
        reason: str,
        *,
        expired: bool = False,
        window: Literal["WAITING", "NONE"] = "NONE",
        dwell: float = 12.0,
        ret_bps: float = 0.0,
    ) -> ReentryTimingDecision:
        return ReentryTimingDecision(
            approved=False,
            expired=expired,
            window=window,
            reason=reason,
            side=norm_side,
            wave_num=int(wave_num) if isinstance(wave_num, int) and not isinstance(wave_num, bool) else 0,
            recommended_preset_chip=None,
            retrace_bps=round(ret_bps, 4),
            min_required_dwell_sec=dwell,
        )

    if not sid:
        return _deny("MISSING_STRATEGY_ID", expired=True)
    if enforce_adr0064_quarantine:
        if (
            sid in QUARANTINED_STRATEGY_IDS_ADR0064
            or sid.startswith("POST_VIX_REVERSAL")
            or "FLOW_VELOCITY_CAPITAL_RECYCLE" in sid
        ):
            return _deny(f"QUARANTINED_ADR0064:{sid}", expired=True)
        if sid not in ACTIVE_CORE_STRATEGY_IDS_ADR0064:
            return _deny(f"NON_CORE_STRATEGY_PAUSED_ADR0064:{sid}", expired=True)
    if dilution_blocked and not is_short:
        return _deny("DF5_SEC_90D_DILUTION_BLOCKED", expired=True)
    if is_short and (easy_to_borrow is not True or shortable is not True or ssr_uptick_compliant is not True):
        return _deny("SHORT_ETB_OR_SSR_GATE_REFUSED", expired=True)

    if isinstance(wave_num, bool) or not isinstance(wave_num, int) or wave_num < 1:
        return _deny("INVALID_WAVE_NUM", expired=True)
    if wave_num > MAX_REENTRY_WAVES:
        return _deny("MAX_3_WAVES_ANTI_CHURN", expired=True)
    if (
        isinstance(symbol_daily_stopouts, bool)
        or not isinstance(symbol_daily_stopouts, int)
        or symbol_daily_stopouts < 0
    ):
        return _deny("INVALID_STOPOUT_COUNTER", expired=True)
    if symbol_daily_stopouts >= SYMBOL_R3A_MAX_DAILY_STOPOUTS:
        return _deny("R3A_SYMBOL_DAILY_STOPOUT_LOCK", expired=True)
    if (
        isinstance(account_consecutive_scratches, bool)
        or not isinstance(account_consecutive_scratches, int)
        or account_consecutive_scratches < 0
    ):
        return _deny("INVALID_SCRATCH_COUNTER", expired=True)
    if account_consecutive_scratches >= DAILY_SCRATCH_MAX_CONSECUTIVE:
        return _deny("DAILY_SCRATCH_STREAK_COOLDOWN", expired=True)

    nums = (
        exit_px,
        live_px,
        vwap_px,
        retrace_extreme_px,
        elapsed_sec,
        ofi_pct,
        spread_bps,
        max_spread_bps,
        account_daily_realized_bps,
    )
    if any(isinstance(x, bool) for x in nums):
        return _deny("INVALID_BOOL_INPUT")
    try:
        ex_f, lv_f, vw_f, mr_f, el_f, ofi_f, sp_f, msp_f, day_bps = (float(x) for x in nums)
    except (TypeError, ValueError):
        return _deny("NONNUMERIC_INPUT")
    if not all(math.isfinite(x) for x in (ex_f, lv_f, vw_f, mr_f, el_f, ofi_f, sp_f, msp_f, day_bps)):
        return _deny("NONFINITE_INPUT")
    if day_bps <= -DAILY_SCRATCH_MAX_LOSS_BPS:
        return _deny("DAILY_SCRATCH_LOSS_BREAKER_HALTED", expired=True)
    if ex_f <= 0.0 or lv_f <= 0.0 or vw_f <= 0.0 or mr_f <= 0.0 or msp_f <= 0.0:
        return _deny("INVALID_NONPOSITIVE_PRICE", expired=True)
    if el_f < 0.0:
        return _deny("NEGATIVE_ELAPSED_CLOCK_SKEW", expired=True)
    if el_f > REENTRY_EXPIRY_SEC:
        return _deny("WINDOW_EXPIRED_300S", expired=True)
    if sp_f <= 0.0 or sp_f > msp_f:
        return _deny("WIDE_SPREAD_COLLAR")

    min_dwell_a = 12.0 if trail_ended else 6.0
    min_retrace_bps = 12.0 if is_mega_large_cap else 25.0
    max_chase_bps = 25.0 if is_mega_large_cap else 50.0
    preset_chip = "S" if (is_mega_large_cap and sp_f <= 8.0) else ("P" if sp_f <= 10.0 else "L")

    if is_short:
        retrace_bps = ((mr_f - ex_f) / ex_f) * 10_000.0
        chase_bps = ((ex_f - lv_f) / ex_f) * 10_000.0
        if mr_f < lv_f:
            return _deny("INCONSISTENT_RETRACE_EXTREME", dwell=min_dwell_a, ret_bps=retrace_bps)
        if mr_f > ex_f * 1.020 or mr_f > vw_f * 1.005:
            return _deny("DEEP_BOUNCE_INVALIDATED", expired=True, dwell=min_dwell_a, ret_bps=retrace_bps)
        if lv_f > vw_f and ofi_f >= 3.0:
            return _deny("SHORT_THESIS_INVALIDATED_ABOVE_VWAP", expired=True, dwell=min_dwell_a, ret_bps=retrace_bps)
        if chase_bps > max_chase_bps:
            return _deny("BOTTOM_CHASE_CAP_EXCEEDED", dwell=min_dwell_a, ret_bps=retrace_bps)

        bounced = (((lv_f - ex_f) / ex_f) * 10_000.0 >= min_retrace_bps) or (retrace_bps >= min_retrace_bps + 2.0)
        no_chase_a = lv_f >= ex_f * 0.9990
        rejected = lv_f <= mr_f
        bounded = lv_f <= ex_f * 1.020 and lv_f <= vw_f * 1.003
        if min_dwell_a <= el_f <= 240.0 and bounced and no_chase_a and rejected and bounded and ofi_f <= -1.5:
            return ReentryTimingDecision(
                approved=True,
                expired=False,
                window="WINDOW_A_BOUNCE_REJECTION",
                reason=f"short_bounce_rejected_after_{el_f:.1f}s_wave_{wave_num}",
                side=norm_side,
                wave_num=wave_num,
                recommended_preset_chip=preset_chip,
                retrace_bps=round(retrace_bps, 4),
                min_required_dwell_sec=min_dwell_a,
            )

        short_coil = lv_f <= vw_f and (ex_f * (1.0 - max_chase_bps / 10_000.0) <= lv_f <= ex_f * 1.0025)
        if 30.0 <= el_f <= REENTRY_EXPIRY_SEC and short_coil and ofi_f <= -3.0:
            return ReentryTimingDecision(
                approved=True,
                expired=False,
                window="WINDOW_B_TIGHT_COIL_CONTINUATION",
                reason=f"short_coil_continuation_after_{el_f:.1f}s_wave_{wave_num}",
                side=norm_side,
                wave_num=wave_num,
                recommended_preset_chip=preset_chip,
                retrace_bps=round(retrace_bps, 4),
                min_required_dwell_sec=30.0,
            )
        return _deny("AWAITING_BOUNCE_OR_COIL_TIMING", window="WAITING", dwell=min_dwell_a, ret_bps=retrace_bps)

    retrace_bps = ((ex_f - mr_f) / ex_f) * 10_000.0
    chase_bps = ((lv_f - ex_f) / ex_f) * 10_000.0
    if mr_f > lv_f:
        return _deny("INCONSISTENT_RETRACE_EXTREME", dwell=min_dwell_a, ret_bps=retrace_bps)
    if mr_f < ex_f * 0.980 or mr_f < vw_f * 0.995:
        return _deny("DEEP_RETRACE_INVALIDATED", expired=True, dwell=min_dwell_a, ret_bps=retrace_bps)
    if lv_f < vw_f and ofi_f <= -3.0:
        return _deny("LONG_THESIS_INVALIDATED_BELOW_VWAP", expired=True, dwell=min_dwell_a, ret_bps=retrace_bps)
    if chase_bps > max_chase_bps:
        return _deny("TOP_CHASE_CAP_EXCEEDED", dwell=min_dwell_a, ret_bps=retrace_bps)

    pulled_back = (((ex_f - lv_f) / ex_f) * 10_000.0 >= min_retrace_bps) or (retrace_bps >= min_retrace_bps + 2.0)
    no_chase_a = lv_f <= ex_f * 1.0010
    rebounded = lv_f >= mr_f
    bounded = lv_f >= ex_f * 0.980 and lv_f >= vw_f * 0.997
    if min_dwell_a <= el_f <= 240.0 and pulled_back and no_chase_a and rebounded and bounded and ofi_f >= 1.5:
        return ReentryTimingDecision(
            approved=True,
            expired=False,
            window="WINDOW_A_PULLBACK_ABSORPTION",
            reason=f"pullback_absorbed_after_{el_f:.1f}s_wave_{wave_num}",
            side=norm_side,
            wave_num=wave_num,
            recommended_preset_chip=preset_chip,
            retrace_bps=round(retrace_bps, 4),
            min_required_dwell_sec=min_dwell_a,
        )

    tight_coil = lv_f >= vw_f and (ex_f * 0.9975 <= lv_f <= ex_f * (1.0 + max_chase_bps / 10_000.0))
    if 30.0 <= el_f <= REENTRY_EXPIRY_SEC and tight_coil and ofi_f >= 3.0:
        return ReentryTimingDecision(
            approved=True,
            expired=False,
            window="WINDOW_B_TIGHT_COIL_CONTINUATION",
            reason=f"tight_coil_continuation_after_{el_f:.1f}s_wave_{wave_num}",
            side=norm_side,
            wave_num=wave_num,
            recommended_preset_chip=preset_chip,
            retrace_bps=round(retrace_bps, 4),
            min_required_dwell_sec=30.0,
        )
    return _deny("AWAITING_PULLBACK_OR_COIL_TIMING", window="WAITING", dwell=min_dwell_a, ret_bps=retrace_bps)


# ---------------------------------------------------------------------------
# 5. 1,000 RPM Alpaca + 3,000 RPM IBKR :4002 Dual-Lane Rate Coordinator
# ---------------------------------------------------------------------------


class DualLane1000RpmRateBudget:
    """Thread-safe dual-lane rate coordinator with isolated `>= 10%` unstarvable protective-exit reserve.

    - Alpaca Algo-Plus Paper lane: `1,000 req/min` (`900` entry cap, `100` isolated exit reserve).
      On HTTP `429`, automatically throttles effective cap to `200 req/min` while keeping an isolated `20/min`
      protective-exit reserve that pre-429 entry bursts can NEVER starve.
    - IBKR Paper `:4002` overflow lane: `3,000 msg/min` & `50 msg/sec` (`2,700/min` & `45/s` entry cap; `300/min` &
      `5/s` isolated exit reserve).
    - TradingView Cloud MCP: `18 calls/min` single-writer delta guard (zero broker-order calls).
    """

    def __init__(
        self,
        *,
        alpaca_max_rpm: int = ALPACA_ALGO_PLUS_MAX_RPM,
        alpaca_exit_reserve_rpm: int = ALPACA_ALGO_PLUS_EXIT_RESERVE_RPM,
        ibkr_port: int = IBKR_PAPER_PORT,
        ibkr_max_mpm: int = IBKR_PAPER_MAX_MPM,
        ibkr_max_per_sec: int = IBKR_PAPER_MAX_PER_SEC,
        tv_mcp_max_rpm: int = TV_CLOUD_MCP_MAX_RPM,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if (
            isinstance(ibkr_port, bool)
            or not isinstance(ibkr_port, int)
            or ibkr_port in FORBIDDEN_LIVE_PORTS
            or ibkr_port not in {4002, 7497}
        ):
            raise ValueError(f"IBKR Paper Firewall: port={ibkr_port} hard-refused")
        if isinstance(alpaca_max_rpm, bool) or not isinstance(alpaca_max_rpm, int) or alpaca_max_rpm < 20:
            raise ValueError(f"alpaca_max_rpm must be int >= 20 (got {alpaca_max_rpm!r})")
        if (
            isinstance(alpaca_exit_reserve_rpm, bool)
            or not isinstance(alpaca_exit_reserve_rpm, int)
            or alpaca_exit_reserve_rpm < math.ceil(alpaca_max_rpm * 0.10)
            or alpaca_exit_reserve_rpm > alpaca_max_rpm
        ):
            raise ValueError("alpaca_exit_reserve_rpm must be int in [ceil(10% of alpaca_max_rpm), alpaca_max_rpm]")
        if isinstance(ibkr_max_mpm, bool) or not isinstance(ibkr_max_mpm, int) or ibkr_max_mpm < 10:
            raise ValueError(f"ibkr_max_mpm must be int >= 10 (got {ibkr_max_mpm!r})")
        if isinstance(ibkr_max_per_sec, bool) or not isinstance(ibkr_max_per_sec, int) or ibkr_max_per_sec < 2:
            raise ValueError(f"ibkr_max_per_sec must be int >= 2 (got {ibkr_max_per_sec!r})")
        if isinstance(tv_mcp_max_rpm, bool) or not isinstance(tv_mcp_max_rpm, int) or not (1 <= tv_mcp_max_rpm <= 40):
            raise ValueError(f"tv_mcp_max_rpm must be int in [1, 40] (got {tv_mcp_max_rpm!r})")

        self.alpaca_nominal_rpm = int(alpaca_max_rpm)
        self.alpaca_nominal_exit_reserve_rpm = int(alpaca_exit_reserve_rpm)
        self.alpaca_effective_rpm = int(alpaca_max_rpm)
        self.alpaca_effective_exit_reserve_rpm = int(alpaca_exit_reserve_rpm)
        self.ibkr_port = int(ibkr_port)
        self.ibkr_max_mpm = int(ibkr_max_mpm)
        self.ibkr_max_per_sec = int(ibkr_max_per_sec)
        self.ibkr_exit_reserve_mpm = max(1, math.ceil(self.ibkr_max_mpm * 0.10))
        self.ibkr_exit_reserve_per_sec = max(1, math.ceil(self.ibkr_max_per_sec * 0.10))
        self.tv_mcp_max_rpm = int(tv_mcp_max_rpm)

        self._clock: Callable[[], float] = clock if clock is not None else time.monotonic
        self._lock = threading.Lock()
        self._last_mono: float | None = None
        self._alpaca_entries: deque[float] = deque()
        self._alpaca_exits: deque[float] = deque()
        self._ibkr_entries: deque[float] = deque()
        self._ibkr_exits: deque[float] = deque()
        self._tv_mcp_calls: deque[float] = deque()

    def _now(self) -> float:
        t = float(self._clock())
        if not math.isfinite(t):
            raise ValueError("Clock returned non-finite timestamp")
        if self._last_mono is not None and t < self._last_mono:
            return self._last_mono
        self._last_mono = t
        return t

    @staticmethod
    def _prune(dq: deque[float], cutoff: float) -> None:
        while dq and dq[0] <= cutoff:
            dq.popleft()

    def note_alpaca_http_429(self) -> None:
        """Downgrade Alpaca bucket to safe 200/min ceiling without ever expanding entry_cap or shrinking reserve below 10%."""
        with self._lock:
            old_rpm = self.alpaca_effective_rpm
            old_reserve = self.alpaca_effective_exit_reserve_rpm
            old_entry_cap = max(0, old_rpm - old_reserve)
            new_rpm = min(old_rpm, ALPACA_HTTP429_FALLBACK_RPM)
            if new_rpm < old_rpm:
                min_reserve_no_expand = max(0, new_rpm - old_entry_cap)
                scaled_reserve = max(
                    ALPACA_HTTP429_EXIT_RESERVE_RPM,
                    math.ceil(new_rpm * 0.10),
                    min_reserve_no_expand,
                )
                self.alpaca_effective_rpm = new_rpm
                self.alpaca_effective_exit_reserve_rpm = min(new_rpm, scaled_reserve)

    def acquire_alpaca(self, *, is_protective_exit: bool = False, count: int = 1) -> bool:
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            return False
        with self._lock:
            now = self._now()
            cutoff = now - 60.0
            self._prune(self._alpaca_entries, cutoff)
            self._prune(self._alpaca_exits, cutoff)
            entry_cap = max(0, self.alpaca_effective_rpm - self.alpaca_effective_exit_reserve_rpm)
            total = len(self._alpaca_entries) + len(self._alpaca_exits)
            if is_protective_exit:
                # Dedicated exit deque guarantees zero starvation even right after HTTP-429 downgrade
                if (len(self._alpaca_exits) + count <= self.alpaca_effective_exit_reserve_rpm) or (
                    total + count <= self.alpaca_effective_rpm
                ):
                    for _ in range(count):
                        self._alpaca_exits.append(now)
                    return True
                return False
            if len(self._alpaca_entries) + count > entry_cap or total + count > entry_cap:
                return False
            for _ in range(count):
                self._alpaca_entries.append(now)
            return True

    def acquire_ibkr(self, *, is_protective_exit: bool = False, count: int = 1) -> bool:
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            return False
        with self._lock:
            now = self._now()
            cutoff_60 = now - 60.0
            cutoff_1 = now - 1.0
            self._prune(self._ibkr_entries, cutoff_60)
            self._prune(self._ibkr_exits, cutoff_60)
            entry_cap_m = self.ibkr_max_mpm - self.ibkr_exit_reserve_mpm
            entry_cap_s = self.ibkr_max_per_sec - self.ibkr_exit_reserve_per_sec
            total_m = len(self._ibkr_entries) + len(self._ibkr_exits)
            e1 = sum(1 for ts in self._ibkr_entries if ts > cutoff_1)
            x1 = sum(1 for ts in self._ibkr_exits if ts > cutoff_1)
            if is_protective_exit:
                m_ok = (len(self._ibkr_exits) + count <= self.ibkr_exit_reserve_mpm) or (
                    total_m + count <= self.ibkr_max_mpm
                )
                s_ok = (x1 + count <= self.ibkr_exit_reserve_per_sec) or (e1 + x1 + count <= self.ibkr_max_per_sec)
                if m_ok and s_ok:
                    for _ in range(count):
                        self._ibkr_exits.append(now)
                    return True
                return False
            if (
                len(self._ibkr_entries) + count > entry_cap_m
                or total_m + count > entry_cap_m
                or e1 + count > entry_cap_s
                or (e1 + x1 + count) > entry_cap_s
            ):
                return False
            for _ in range(count):
                self._ibkr_entries.append(now)
            return True

    def acquire_tv_cloud_mcp(self, count: int = 1) -> bool:
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            return False
        with self._lock:
            now = self._now()
            self._prune(self._tv_mcp_calls, now - 60.0)
            if len(self._tv_mcp_calls) + count > self.tv_mcp_max_rpm:
                return False
            for _ in range(count):
                self._tv_mcp_calls.append(now)
            return True

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            now = self._now()
            cutoff = now - 60.0
            self._prune(self._alpaca_entries, cutoff)
            self._prune(self._alpaca_exits, cutoff)
            self._prune(self._ibkr_entries, cutoff)
            self._prune(self._ibkr_exits, cutoff)
            self._prune(self._tv_mcp_calls, cutoff)
            return {
                "alpaca_effective_rpm": self.alpaca_effective_rpm,
                "alpaca_exit_reserve_rpm": self.alpaca_effective_exit_reserve_rpm,
                "alpaca_used_entries": len(self._alpaca_entries),
                "alpaca_used_exits": len(self._alpaca_exits),
                "ibkr_port": self.ibkr_port,
                "ibkr_max_mpm": self.ibkr_max_mpm,
                "ibkr_exit_reserve_mpm": self.ibkr_exit_reserve_mpm,
                "ibkr_used_entries": len(self._ibkr_entries),
                "ibkr_used_exits": len(self._ibkr_exits),
                "tv_mcp_max_rpm": self.tv_mcp_max_rpm,
                "tv_mcp_used": len(self._tv_mcp_calls),
            }


# ---------------------------------------------------------------------------
# 6. Contract Validator, Firewall Gate & SHA-256 Sealed Manifest Builder
# ---------------------------------------------------------------------------


def validate_tv_preset_and_route_firewall(
    *,
    presets: Sequence[Mapping[str, Any]],
    target_port: int,
    target_host: str = "127.0.0.1",
    bridge_name: str = "local_loopback_kernel",
) -> tuple[bool, list[str]]:
    """Fail-closed firewall verifying 6 uncapped presets (`TP OFF`), paper-only port, and zero SaaS execution relay."""
    errors: list[str] = []
    bridge_low = str(bridge_name or "").strip().lower()
    for bad in HARD_REFUSED_EXECUTION_SAAS_BRIDGES:
        if bad in bridge_low:
            errors.append(f"HARD_REFUSED_EXECUTION_SAAS:{bad}")

    host_low = str(target_host or "").strip().lower()
    allowed_paper_hosts = {
        "127.0.0.1",
        "localhost",
        "::1",
        "paper-api.alpaca.markets",
        "100.110.115.22",
        "100.93.211.101",
    }
    if host_low not in allowed_paper_hosts:
        if any(fh in host_low for fh in FORBIDDEN_LIVE_HOSTS):
            errors.append(f"LIVE_HOST_HARD_REFUSED:{target_host}")
        elif any(bad in host_low for bad in HARD_REFUSED_EXECUTION_SAAS_BRIDGES):
            errors.append(f"HARD_REFUSED_SAAS_HOST:{target_host}")
        else:
            errors.append(f"UNSANCTIONED_OR_LIVE_HOST:{target_host}")
    if isinstance(target_port, bool) or not isinstance(target_port, int) or target_port in FORBIDDEN_LIVE_PORTS:
        errors.append(f"LIVE_PORT_HARD_REFUSED:{target_port}")
    elif target_port not in ALLOWED_PAPER_PORTS:
        errors.append(f"UNSANCTIONED_PORT:{target_port}")

    seen_chips: list[str] = []
    for p in presets:
        chip = str(p.get("chip") or "").strip().upper()
        seen_chips.append(chip)
        raw_cfg = p.get("tv_ticket_config")
        cfg: Mapping[str, Any] = raw_cfg if isinstance(raw_cfg, Mapping) else {}
        if bool(cfg.get("tp_enabled")):
            errors.append(f"PRESET_FIXED_TP_FORBIDDEN_ADR0063:{chip}")
        if str(cfg.get("quantity_type") or "") != "Shares":
            errors.append(f"PRESET_FRACTIONAL_QTY_FORBIDDEN_42210000:{chip}")
        sl_pct = cfg.get("sl_pct_price")
        if sl_pct is not None:
            try:
                sl_f = float(_to_strict_decimal(sl_pct, "sl_pct_price"))
                if sl_f <= 0.0 or sl_f > ADR0022_MAX_STOP_PCT_FLOAT:
                    errors.append(f"PRESET_ADR0022_STOP_EXCEEDED:{chip}:{sl_f}")
            except ValueError:
                errors.append(f"PRESET_INVALID_STOP:{chip}")

    missing = [c for c in UNCAPPED_QUICKBAR_CHIPS if c not in seen_chips]
    if missing:
        errors.append(f"MISSING_UNCAPPED_PRESET_CHIPS:{','.join(missing)}")

    return len(errors) == 0, errors


def build_tv_multilayout_foundation_manifest() -> dict[str, Any]:
    """Assemble deterministic SHA-256-sealed open-core TradingView landscape & multi-layout manifest."""
    class_counts: dict[str, int] = {}
    for item in TV_LIBRARY_LANDSCAPE_STACK:
        c = str(item["capability_class"])
        class_counts[c] = class_counts.get(c, 0) + 1

    core: dict[str, Any] = {
        "schema_version": TV_LANDSCAPE_CONTRACT_SCHEMA,
        "adr": "ADR-0045",
        "promotion_track": "PROTECTIVE_FILTER_OR_GOVERNANCE",
        "standalone_alpha_claim": False,
        "dimensionless_privacy_firewall": True,
        "order_authority_on_visual_surfaces": False,
        "visual_artifacts_may_bind_alert_or_webhook": False,
        "library_landscape_count": len(TV_LIBRARY_LANDSCAPE_STACK),
        "library_class_counts": class_counts,
        "library_landscape_stack": list(TV_LIBRARY_LANDSCAPE_STACK),
        "multi_layouts_count": len(CANONICAL_TV_MULTI_LAYOUTS),
        "multi_layouts": list(CANONICAL_TV_MULTI_LAYOUTS),
        "quickbar_uncapped_chips": list(UNCAPPED_QUICKBAR_CHIPS),
        "largecap_micro_trail_contract": {
            "trail_band_bps": [LARGECAP_MIN_TRAIL_BPS, LARGECAP_MAX_TRAIL_BPS],
            "be_arm_band_bps": [LARGECAP_BE_ARM_MIN_BPS, LARGECAP_BE_ARM_MAX_BPS],
            "max_spread_bps": LARGECAP_MAX_SPREAD_BPS,
            "adr0022_max_initial_stop_pct": ADR0022_MAX_STOP_PCT_FLOAT,
            "sub_venue_synthetic_guardian_interval_sec": 1.1,
            "take_profit_cap_enabled": False,
        },
        "fast_reentry_contract": {
            "max_waves_per_symbol": MAX_REENTRY_WAVES,
            "expiry_sec": REENTRY_EXPIRY_SEC,
            "window_a_dwell_partial_sec": 6.0,
            "window_a_dwell_full_exit_sec": 12.0,
            "window_b_coil_min_sec": 30.0,
            "largecap_min_retrace_bps": 12.0,
            "standard_min_retrace_bps": 25.0,
            "r3a_max_symbol_stopouts": SYMBOL_R3A_MAX_DAILY_STOPOUTS,
            "daily_scratch_max_loss_bps": DAILY_SCRATCH_MAX_LOSS_BPS,
        },
        "dual_lane_rate_contract": {
            "alpaca_algo_plus_rpm": ALPACA_ALGO_PLUS_MAX_RPM,
            "alpaca_exit_reserve_rpm": ALPACA_ALGO_PLUS_EXIT_RESERVE_RPM,
            "alpaca_http429_fallback_rpm": ALPACA_HTTP429_FALLBACK_RPM,
            "alpaca_http429_exit_reserve_rpm": ALPACA_HTTP429_EXIT_RESERVE_RPM,
            "ibkr_paper_port": IBKR_PAPER_PORT,
            "ibkr_paper_max_mpm": IBKR_PAPER_MAX_MPM,
            "ibkr_paper_exit_reserve_mpm": IBKR_PAPER_EXIT_RESERVE_MPM,
            "tv_cloud_mcp_max_rpm": TV_CLOUD_MCP_MAX_RPM,
            "forbidden_live_ports": sorted(FORBIDDEN_LIVE_PORTS),
            "hard_refused_live_hosts": [
                f"{h} (hard-refused live-capital endpoint)" for h in sorted(FORBIDDEN_LIVE_HOSTS)
            ],
            "live_capital_firewall_policy": "hard-refused unconditionally",
        },
    }
    digest = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    return {**core, "manifest_sha256": digest}
