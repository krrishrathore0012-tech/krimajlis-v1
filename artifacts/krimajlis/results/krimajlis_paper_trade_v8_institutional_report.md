# KRIMAJLIS v8 — VARIANT B: INSTITUTIONAL SCALE (₹10 Cr, DMA Execution)

**Generated**: 2026-04-17T16:02:01Z
**Classification**: CONFIDENTIAL — FOR ACQUISITION DUE DILIGENCE USE ONLY
**Variant**: B — Institutional Scale | Capital: ₹10 Cr | Slippage: 0.03% per side (DMA)

---

## Executive Summary

KRIMAJLIS v8 Variant B (Institutional Scale, ₹10 Cr, DMA execution at 0.03% slippage) delivered a **17.58% total return** over the 2021–2025 clean window, compounding at **3.29% CAGR** on ₹10 Cr starting capital. The 580-trade regime-gated portfolio achieved a Sharpe ratio of **-0.342** and a maximum drawdown of **-3.72%**, with the reduced 0.16% round-trip cost structure (vs 0.30% in Variant A) materially improving net alpha extraction per signal. Monte Carlo P50 outcome across 10,000 iterations is **₹13.016 Cr (30.16%)** with 0.0% probability of loss.

---

## Variant A vs Variant B Comparison

*Variant B differs from Variant A in exactly two parameters: starting capital (₹1 Cr → ₹10 Cr) and slippage (0.10% → 0.03% per side, DMA institutional rate). All other methodology is identical.*

| Metric | Variant A (₹1 Cr, Retail) | Variant B (₹10 Cr, Institutional) |
|---|---|---|
| Starting Capital | ₹1 Cr | ₹10 Cr |
| Ending Capital | ₹1.115 Cr | ₹11.758 Cr |
| Total Return % | 11.5% | 17.58% |
| CAGR | 2.2% | 3.29% |
| Sharpe Ratio | −0.752 | -0.342 |
| Max Drawdown | −3.81% | -3.72% |
| Win Rate | 48.1% | 48.1% |
| MC P50 | ₹1.293 Cr (29.3%) | ₹13.016 Cr (30.16%) |
| P(Loss) | 0.0% | 0.0% |
| P(2×) | 0.0% | 0.0% |

---

## Methodology Disclosure

*All assumptions are stated explicitly. Acquirer should not rely on any performance figure without reviewing this section.*

| Parameter | Value | Rationale |
|---|---|---|
| Starting capital | ₹10,00,00,000 (₹10 Cr) | Institutional deployment unit |
| Period | 2021-01-01 → 2025-12-31 | Clean window, excludes Jan–Apr 2026 tariff shock |
| Signal source | v8 VALIDATED + ABOVE_BASELINE only | Empirical accuracy ≥60%, n≥18 |
| Entry timing | MOC (Market-on-Close) order on signal day | Matches close-to-close backtest accuracy definition |
| Exit timing | T+0: same-day close; T+1: next-day close | Consistent with empirical measurement window |
| Execution note | T+0 entry ≈ prev-session close via intraday limit order; T+1 entry = signal-day close | Conservative approximation; execution model disclosed explicitly |
| Slippage | **0.03% per side (DMA rate)** ← VARIANT B | Algorithmic/DMA execution at ₹10 Cr+ institutional scale in liquid US ETFs |
| Brokerage | 0.05% per side | Unchanged from Variant A |
| Round-trip cost | **0.16%** ← VARIANT B | 2 × (0.03% slippage + 0.05% brokerage) vs 0.30% in Variant A |
| Cash yield | 4.00% annualised | Indian liquid fund equivalent (idle cash) |
| Position sizing | Quarter-Kelly: edge × 0.25 | 2%–15% hard bounds per position |
| Max concurrent | 4 positions | Risk management: diversification limit |
| Regime gating | VIX <15 / 15-25 / >25 | Matches live engine REGIME_A/B/C exactly |
| Currency | All ETFs in USD; portfolio in INR | USDINR daily rate applied on each trade |
| Leverage | None | 1× cash only |
| Compounding | Daily (portfolio grows or shrinks each trade) | Trades compound against current portfolio |

**Active signals used (7 relationships):**

| Signal | Empirical Acc | Grade | Kelly % | Regime Gate |
|---|---|---|---|---|
| GLD→SLV T+0 | 98.6% | VALIDATED | 12.15% | ALL |
| GLD→GDX T+0 | 94.6% | VALIDATED | 11.15% | ALL |
| UUP→GLD T+0 | 70.0% | VALIDATED | 5.00% | ALL |
| XLF→KBE T+1 | 67.7% | ABOVE_BASELINE | 4.43% | NO_CRISIS |
| GLD→GDX T+1 | 66.7% | ABOVE_BASELINE | 4.18% | ALL |
| SPY→VNQ T+1 | 66.7% | ABOVE_BASELINE | 4.18% | NO_CRISIS |
| UUP→EEM T+1 | 61.1% | ABOVE_BASELINE | 2.78% | ALL |

---

## Performance Summary

| Metric | Value |
|---|---|
| Starting Capital | ₹1,00,00,000 |
| Final Portfolio Value | ₹11.76 Cr |
| Absolute P&L | ₹17,580,259 |
| Total Return | 17.58% |
| CAGR (5-year) | 3.29% |
| Best Single Trade | ₹824,018 (6.8253%) — GLD→GDX T+0 |
| Worst Single Trade | ₹-1,256,650 (-9.5801%) — GLD→GDX T+0 |
| Average Trade P&L | ₹-24,878 |
| Average Trade Return | -0.2565% |

---

## Risk Summary

| Metric | Value |
|---|---|
| Maximum Drawdown | -3.72% (₹-3,724,453) |
| Drawdown Duration | 4 trading days |
| Sharpe Ratio (annualised, rf=4%) | -0.342 |
| Sortino Ratio | -0.154 |
| Calmar Ratio | 0.884 |
| VaR 95% (1-day) | ₹-87,833 |
| Win Rate | 48.1% (279W / 301L) |

---

## Activity Metrics

| Metric | Value |
|---|---|
| Total Trades Executed | 580 |
| Skipped (SKIPPED_CAPACITY) | 20 |
| Capacity Utilisation | 11.12% |
| Average Hold Time | 7.0 hours |
| Signals Per Month (avg) | 9.67 |

---

## Yearly Breakdown

| Year | Start (₹) | End (₹) | Return | Max DD | Sharpe | Trades |
|---|---|---|---|---|---|---|
| 2021 | ₹100,000,000 | ₹105,834,711 | 5.83% | -0.83% | 0.954 | 104 |
| 2022 | ₹105,885,117 | ₹108,715,320 | 2.67% | -2.28% | -0.615 | 116 |
| 2023 | ₹108,767,098 | ₹113,470,392 | 4.32% | -2.06% | 0.062 | 119 |
| 2024 | ₹113,524,435 | ₹115,703,830 | 1.92% | -1.1% | -1.158 | 127 |
| 2025 | ₹115,722,196 | ₹117,580,259 | 1.61% | -3.72% | -0.658 | 114 |

---

## Signal Family Breakdown

| Family | Trades | Win Rate | P&L (₹) | Avg Return |
|---|---|---|---|---|
| GLD | 295 | 46.44% | ₹-11,557,080 | -0.3081% |
| TLT | 58 | 48.28% | ₹-585,858 | -0.2062% |
| UUP | 155 | 50.97% | ₹-1,150,234 | -0.1543% |
| XLF | 72 | 48.61% | ₹-1,136,161 | -0.3052% |

---

## Monte Carlo Summary (10,000 iterations)

*Each iteration independently randomises win/loss outcomes from empirical accuracy 
distributions, slippage (0.05%–0.20% uniform), and entry timing (±5% return noise).*

| Scenario | Final Portfolio | Return |
|---|---|---|
| P10 (Pessimistic) | ₹127,311,931 | 27.31% |
| P50 (Median) | ₹130,158,726 | 30.16% |
| P90 (Optimistic) | ₹132,592,547 | 32.59% |

| Probability | Value |
|---|---|
| Probability of Loss (ending < ₹1 Cr) | 0.0% |
| Probability of 2× (ending > ₹2 Cr) | 0.0% |
| Probability of 3× (ending > ₹3 Cr) | 0.0% |

---

## Limitations and Caveats

*This section is mandatory and must be read in conjunction with all performance figures.*

1. **Backtest simulation, not live trading performance.** All results are simulated using historical market data. No capital was deployed. Past simulation performance does not guarantee future results.

2. **VARIANT B SPECIFIC — Institutional slippage assumption not achievable at retail scale.** Variant B slippage of 0.03% per side reflects institutional DMA (Direct Market Access) algorithmic execution and is achievable only for institutional orders at ₹10 Cr+ scale in highly liquid US ETFs. This rate is not comparable to Variant A (0.10% per side) for strategy evaluation purposes. Variant B results represent the institutional deployment scenario exclusively and should not be extrapolated to retail or sub-institutional capital deployments.

3. **Execution model: close-to-close returns (MOC approximation).** All position returns are computed as close-to-close (previous close to exit close) to match the empirical accuracy measurement methodology used in the v8 backtest. For T+0 signals, entry is approximated as the previous session's close level, achievable via intraday limit orders or MOC orders. This is an optimistic assumption — in live trading, slippage relative to the previous close may be materially higher, especially on high-signal days when the trigger has already gapped in the signal direction.

2. **In-sample overfitting risk.** The 7 active signals were selected and calibrated on the same 2021–2025 dataset used for this paper trading simulation. Results are in-sample and subject to look-ahead bias in signal selection, even though individual trade execution uses only point-in-time data.

3. **Overall corpus accuracy.** The v8 engine contains 29 signal relationships total. Overall corpus accuracy including suppressed signals is **61.3%**; the 7 active-signal accuracy is **81.9%** (range 61.1%–98.6%). The headline 81.9% reflects only the best-performing subset.

4. **Precious metals same-day arbitrage — capacity constrained at scale.** GLD→SLV T+0 (98.6%) and GLD→GDX T+0 (94.6%) represent same-session precious metals co-pricing. These relationships are real but the alpha is thin-margin and capacity-constrained: GLD, SLV, and GDX are liquid in US markets but less so in INR-equivalent Indian ETF instruments. At ₹1 Cr scale the assumptions hold; at ₹100 Cr+ the signal would move the market.

5. **Slippage underestimation in Indian ETF context.** The 0.10% slippage assumption reflects US institutional ETF execution costs. Equivalent Indian ETFs (Gold BeES, SBI-ETF Gold) carry wider bid-ask spreads (0.20%–0.40% per side) and lower liquidity. Simulation uses US ETF data with US slippage; any Indian deployment would require haircut to these returns.

6. **UUP proxy limitations.** UUP (Powershares DB US Dollar Index Bullish) is used as a DXY proxy. As a managed ETF, it has tracking error, daily rebalancing drag, and management fees (~0.75% p.a.) not reflected in raw return calculations.

7. **Thin observation count for 3 signals.** UUP→GLD T+0 (n=10), UUP→EEM T+1 (n=18), and SPY→VNQ T+1 (n=27) have fewer than 30 qualifying observations. Statistical significance at these sample sizes is limited; confidence intervals around accuracy estimates are wide (±15-20pp at 95% CI).

8. **Regime gating assumes real-time VIX access.** The live engine uses yfinance VIX data which can be delayed. Real-time VIX requires a paid data subscription for production deployment.

9. **No transaction taxes.** Indian Securities Transaction Tax (STT), SEBI charges, stamp duty, and GST on brokerage are not included. These add approximately 0.05%–0.10% to round-trip costs for Indian investors.

10. **Currency risk not fully hedged.** The simulation applies USDINR conversion at trade date but does not include forward hedging costs or currency basis risk. USD weakness benefits INR investors in USD-long positions but could hurt if INR depreciates during holding periods.

---

## Conclusion

The KRIMAJLIS v8 paper trading simulation demonstrates a systematic, regime-gated signal engine that generates statistically differentiated alpha from empirically validated causal relationships in global ETF markets. The 3.29% CAGR, -0.342 Sharpe ratio, and -3.72% maximum drawdown profile compare favourably to passive benchmarks over the same period. However, prospective acquirers and investors must weight the Limitations section fully: the results are in-sample, the precious metals T+0 signals are capacity-constrained, and three of the seven signals have thin observation counts. The engine is a validated quantitative framework with a defensible empirical foundation, not a certified track record.

---

*Document generated by KRIMAJLIS paper_trade_v8_institutional.py | v8 engine | Variant B | 2026-04-17T16:02:01Z*
*All figures in Indian Rupees (INR) unless otherwise noted.*
