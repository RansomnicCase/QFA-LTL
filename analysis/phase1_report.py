import json

data = json.load(open('outputs/phase1/phase1_results_20260816_211721.json'))
agg = data['aggregated']

print('='*70)
print('PHASE 1 RESULTS — 10 seeds x 5 strategies x 24 circuits x 3 reps')
print('='*70)
print(f'{"Strategy":<15} {"Recall":>10} {"Precision":>10} {"False-Fail":>10} {"F1":>10}')
print('-'*55)
for name in ['adaptive_zkc', 'fixed', 'hoeffding', 'wilson', 'no_zkc']:
    a = agg[name]
    r = f'{a["recall_mean"]:.3f} ({a["recall_ci"][0]:.3f}-{a["recall_ci"][1]:.3f})'
    p = f'{a["precision_mean"]:.3f} ({a["precision_ci"][0]:.3f}-{a["precision_ci"][1]:.3f})'
    ff = f'{a["false_failure_rate_mean"]:.3f} ({a["false_failure_rate_ci"][0]:.3f}-{a["false_failure_rate_ci"][1]:.3f})'
    f1 = f'{a["f1_mean"]:.3f} ({a["f1_ci"][0]:.3f}-{a["f1_ci"][1]:.3f})'
    print(f'{name:<15} {r:>22} {p:>22} {ff:>22} {f1:>22}')

print()
print('='*70)
print('McNemar TESTS (adaptive_zkc vs baselines)')
print('='*70)

# Re-run McNemar from raw results
from collections import defaultdict
import numpy as np
from scipy import stats

def mcnemar_test(results_a, results_b):
    lookup_a = {r['circuit']: r for r in results_a}
    lookup_b = {r['circuit']: r for r in results_b}
    b_wins = 0
    a_wins = 0
    for name in lookup_a:
        if name not in lookup_b:
            continue
        a_passed = lookup_a[name]['passed']
        b_passed = lookup_b[name]['passed']
        if a_passed and not b_passed:
            a_wins += 1
        elif not a_passed and b_passed:
            b_wins += 1
    total_discordant = a_wins + b_wins
    if total_discordant == 0:
        return {'statistic': 0.0, 'p_value': 1.0, 'a_wins': 0, 'b_wins': 0}
    statistic = (abs(a_wins - b_wins) - 1) ** 2 / total_discordant
    p_value = 1 - stats.chi2.cdf(statistic, df=1)
    return {'statistic': statistic, 'p_value': p_value, 'a_wins': a_wins, 'b_wins': b_wins}

raw = data['raw']
adaptive_results = []
for seed in raw['adaptive_zkc'].values():
    adaptive_results.extend(seed)

for strat_name in ['fixed', 'hoeffding', 'wilson', 'no_zkc']:
    baseline_results = []
    for seed in raw[strat_name].values():
        baseline_results.extend(seed)
    test = mcnemar_test(adaptive_results, baseline_results)
    sig = "***" if test['p_value'] < 0.001 else "**" if test['p_value'] < 0.01 else "*" if test['p_value'] < 0.05 else "ns"
    print(f'adaptive_zkc vs {strat_name:<12s}: p={test["p_value"]:.4f} {sig}  (adaptive wins {test["a_wins"]}, baseline wins {test["b_wins"]})')
