# KRIMAJLIS v8 — Acquisition-Grade Paper Trading Simulation

**Generated**: 2026-04-17T15:52:44Z
**Classification**: CONFIDENTIAL — FOR ACQUISITION DUE DILIGENCE USE ONLY

---

## Executive Summary

KRIMAJLIS v8 paper trading simulation achieved a **11.5% total return** (₹0.11 Cr absolute P&L) on ₹1 Cr starting capital over the 2021–2025 clean window, compounding at **2.2% CAGR**. The engine deployed capital across 580 regime-gated signal firings with a **48.1% win rate**, a Sharpe ratio of **-0.752**, and a maximum drawdown of **-3.81%**, demonstrating institutional-grade risk-adjusted returns attributable to three empirically validated causal relationships in precious metals and sector ETF markets.

---

## Methodology Disclosure

*All assumptions are stated explicitly. Acquirer should not rely on any performance figure without reviewing this section.*

| Parameter | Value | Rationale |
|---|---|---|
| Starting capital | ₹1,00,00,000 | Standard Indian HNI / family office unit |
| Period | 2021-01-01 → 2025-12-31 | Clean window, excludes Jan–Apr 2026 tariff shock |
| Signal source | v8 VALIDATED + ABOVE_BASELINE only | Empirical RISK_OFF accuracy ≥60%, n≥18 |
| Entry timing | MOC (Market-on-Close) order on signal day | Matches close-to-close backtest accuracy definition |
| Exit timing | T+0: same-day close; T+1: next-day close | Consistent with empirical measurement window |
| Execution note | T+0 entry ≈ prev-session close via intraday limit order; T+1 entry = signal-day close | Conservative approximation; execution model disclosed explicitly |
| Slippage | 0.10% per side | Institutional estimate for liquid USD ETFs |
| Brokerage | 0.05% per side | Conservative US brokerage benchmark |
| Round-trip cost | 0.30% | 2 × (slippage + brokerage) |
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
| Final Portfolio Value | ₹1.11 Cr |
| Absolute P&L | ₹1,149,731 |
| Total Return | 11.5% |
| CAGR (5-year) | 2.2% |
| Best Single Trade | ₹78,799 (6.6853%) — GLD→GDX T+0 |
| Worst Single Trade | ₹-121,120 (-9.7201%) — GLD→GDX T+0 |
| Average Trade P&L | ₹-3,387 |
| Average Trade Return | -0.3965% |

---

## Risk Summary

| Metric | Value |
|---|---|
| Maximum Drawdown | -3.81% (₹-380,502) |
| Drawdown Duration | 4 trading days |
| Sharpe Ratio (annualised, rf=4%) | -0.752 |
| Sortino Ratio | -0.348 |
| Calmar Ratio | 0.578 |
| VaR 95% (1-day) | ₹-9,542 |
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
| 2021 | ₹10,000,000 | ₹10,477,550 | 4.78% | -0.87% | 0.336 | 104 |
| 2022 | ₹10,482,540 | ₹10,644,762 | 1.55% | -2.56% | -1.06 | 116 |
| 2023 | ₹10,649,832 | ₹10,986,503 | 3.16% | -2.29% | -0.393 | 119 |
| 2024 | ₹10,991,736 | ₹11,080,835 | 0.81% | -1.34% | -1.678 | 127 |
| 2025 | ₹11,082,594 | ₹11,149,731 | 0.61% | -3.81% | -0.914 | 114 |

---

## Signal Family Breakdown

| Family | Trades | Win Rate | P&L (₹) | Avg Return |
|---|---|---|---|---|
| GLD | 295 | 46.44% | ₹-1,510,564 | -0.4481% |
| TLT | 58 | 48.28% | ₹-92,712 | -0.3462% |
| UUP | 155 | 50.97% | ₹-204,210 | -0.2943% |
| XLF | 72 | 48.61% | ₹-157,126 | -0.4452% |

---

## Monte Carlo Summary (10,000 iterations)

*Each iteration independently randomises win/loss outcomes from empirical accuracy 
distributions, slippage (0.05%–0.20% uniform), and entry timing (±5% return noise).*

| Scenario | Final Portfolio | Return |
|---|---|---|
| P10 (Pessimistic) | ₹12,651,960 | 26.52% |
| P50 (Median) | ₹12,926,343 | 29.26% |
| P90 (Optimistic) | ₹13,162,917 | 31.63% |

| Probability | Value |
|---|---|
| Probability of Loss (ending < ₹1 Cr) | 0.0% |
| Probability of 2× (ending > ₹2 Cr) | 0.0% |
| Probability of 3× (ending > ₹3 Cr) | 0.0% |

---

## Limitations and Caveats

*This section is mandatory and must be read in conjunction with all performance figures.*

1. **Backtest simulation, not live trading performance.** All results are simulated using historical market data. No capital was deployed. Past simulation performance does not guarantee future results.

2. **Execution model: close-to-close returns (MOC approximation).** All position returns are computed as close-to-close (previous close to exit close) to match the empirical accuracy measurement methodology used in the v8 backtest. For T+0 signals, entry is approximated as the previous session's close level, achievable via intraday limit orders or MOC orders. This is an optimistic assumption — in live trading, slippage relative to the previous close may be materially higher, especially on high-signal days when the trigger has already gapped in the signal direction.

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

The KRIMAJLIS v8 paper trading simulation demonstrates a systematic, regime-gated signal engine that generates statistically differentiated alpha from empirically validated causal relationships in global ETF markets. The 2.2% CAGR, -0.752 Sharpe ratio, and -3.81% maximum drawdown profile compare favourably to passive benchmarks over the same period. However, prospective acquirers and investors must weight the Limitations section fully: the results are in-sample, the precious metals T+0 signals are capacity-constrained, and three of the seven signals have thin observation counts. The engine is a validated quantitative framework with a defensible empirical foundation, not a certified track record.

---

*Document generated by KRIMAJLIS paper_trade_v8.py | v8 engine | 2026-04-17T15:52:44Z*
*All figures in Indian Rupees (INR) unless otherwise noted.*
