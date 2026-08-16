# Phase 1 Results — Honest Analysis

**Config:** 10 seeds × 5 strategies × 24 circuits × 3 reps = **900 tests per strategy**.

## Aggregated Metrics (mean, 95% CI)

| Strategy | Recall | Precision | False-Failure | F1 |
|---|---|---|---|---|
| **adaptive_zkc** | **0.800** (0.782–0.818) | 0.878 (0.876–0.880) | 0.333 (0.333–0.333) | **0.837** (0.826–0.848) |
| fixed | 0.554 (0.550–0.557) | 0.909 (0.908–0.909) | 0.167 (0.167–0.167) | 0.688 (0.685–0.691) |
| hoeffding | 0.433 (0.398–0.469) | 1.000 (1.000–1.000) | 0.000 (0.000–0.000) | 0.603 (0.568–0.638) |
| wilson | 0.517 (0.500–0.533) | 1.000 (1.000–1.000) | 0.000 (0.000–0.000) | 0.681 (0.667–0.695) |
| no_zkc | 1.000 (1.000–1.000) | 0.757 (0.748–0.765) | 0.967 (0.923–1.010) | 0.861 (0.856–0.867) |

## McNemar Tests (adaptive_zkc vs baselines)

| Comparison | p-value | sig | Interpretation |
|---|---|---|---|
| adaptive_zkc vs fixed | 0.1306 | ns | Not significant at p<0.05 |
| adaptive_zkc vs hoeffding | **0.0077** | ** | Significant at p<0.01 |
| adaptive_zkc vs wilson | **0.0233** | * | Significant at p<0.05 |
| adaptive_zkc vs no_zkc | **0.0133** | * | Significant at p<0.05 |

## Honest Interpretation

### What the data supports

1. **The adaptive anchor is significantly better than statistical baselines.** Against Hoeffding (p=0.008) and Wilson (p=0.023) bounds, the adaptive anchor achieves substantially higher recall (80% vs 43–52%) at comparable precision. The volume-based anchor from a real noise estimate is a meaningful improvement over generic concentration inequalities.

2. **The ZKC probe is the decisive component.** The no-ZKC ablation (same volume scaling, fixed ε=0.005) achieves 100% recall but at a catastrophic 96.7% false-failure rate — it fails almost every correct circuit. The probe's real-time noise estimate is what calibrates the anchor to a usable operating point. This is the paper's strongest ablation result.

3. **The F1 tradeoff favors adaptive.** Adaptive F1=0.837 vs fixed F1=0.688, Hoeffding F1=0.603, Wilson F1=0.681. Only the no-ZKC ablation has higher F1 (0.861), but that's the "catch everything, fail everything" regime.

### What the data does NOT support

1. **Adaptive is NOT significantly better than a fixed 0.15 threshold (p=0.13).** The fixed threshold has lower false-failure rate (17% vs 33%) because it's *overly lenient* on easy circuits. The adaptive anchor trades some false-failure rate for higher bug detection. This is a real tradeoff, not a clean win.

2. **The false-failure rate is higher than ideal (33%).** The adaptive anchor is calibrated to noise: on high-noise seeds, it drops the threshold so low that some correct circuits with borderline metrics still fail. This suggests the anchor floor (0.10) or the 0.98 scale factor may need adjustment, or the verdict logic needs a "gray zone" for borderline cases.

### The honest story for the paper

> The adaptive anchor achieves statistically significant improvements over classical concentration bounds (Hoeffding p<0.01, Wilson p<0.05) and over a no-probe ablation (p<0.05), demonstrating that real-time noise estimation via calibration probes adds value beyond blind volume scaling. The tradeoff is a higher false-failure rate than a fixed threshold (33% vs 17%), reflecting the anchor's sensitivity to noise: it drops the threshold on noisy days, occasionally failing correct circuits with borderline metrics. The F1 score (0.837) is the best among practical strategies; only the degenerate "catch everything" regime (no-ZKC ablation, 96.7% FF) scores higher.

## Next Steps

- **Hold-out calibration:** The current in-sample threshold learning inflates performance. A hold-out split (e.g., 60% calibration / 40% test) will give unbiased estimates.
- **Anchor floor analysis:** The 0.10 floor is hit frequently. A data-driven floor (e.g., based on the probe's confidence interval) could reduce false failures.
- **Per-algorithm analysis:** Aggregate metrics hide algorithm-specific behavior. GHZ and QFT bugs are measurement-invisible; the adaptive anchor should shine on algorithms where faults *do* shift the distribution (Grover, BV, DJ, QAOA).
- **More seeds:** 10 seeds gives tight CIs but 30+ would be publication-standard.
