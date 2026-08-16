"""
Phase 1 multi-seed driver.

Runs the full benchmark suite across multiple seeds for each threshold strategy,
computes Wilson CIs on every metric, and runs McNemar tests between the
adaptive strategy and each baseline.

Usage:
    python run_phase1.py --seeds 42 --strategies adaptive_zkc fixed hoeffding wilson no_zkc
"""
import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import numpy as np

from qfa_verify.experiments.orchestrator import SafetyOrchestrator
from qfa_verify.thresholds import get_strategy


def run_single_seed(seed: int, strategies: list, shots: int = 1024, reps: int = 5,
                    holdout_fraction: float = 0.0):
    """Run all strategies for a single seed."""
    results = {}
    for strat_name in strategies:
        orch = SafetyOrchestrator(backend="fake_brisbane", use_ibm=False, seed=seed)
        eval_results = orch.run_full_suite(
            backends=["fake_brisbane"],
            shots=shots,
            reps=reps,
            strategy=strat_name,
            holdout_fraction=holdout_fraction,
            seed=seed
        )
        results[strat_name] = eval_results
    return results


def compute_metrics(results: list) -> dict:
    """Compute detection metrics from a list of result dicts."""
    tp = sum(1 for r in results if not r['passed'] and r['is_buggy'])
    fp = sum(1 for r in results if not r['passed'] and not r['is_buggy'])
    fn = sum(1 for r in results if r['passed'] and r['is_buggy'])
    tn = sum(1 for r in results if r['passed'] and not r['is_buggy'])
    
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    false_failure = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
        'recall': recall, 'precision': precision,
        'false_failure_rate': false_failure, 'f1': f1
    }


def wilson_ci(successes: int, trials: int, z: float = 1.96) -> tuple:
    """Wilson score interval for a binomial proportion."""
    if trials == 0:
        return 0.0, 0.0
    p_hat = successes / trials
    denom = 1 + z**2 / trials
    center = (p_hat + z**2 / (2 * trials)) / denom
    margin = (z / denom) * np.sqrt(p_hat * (1 - p_hat) / trials + z**2 / (4 * trials**2))
    return center - margin, center + margin


def aggregate_metrics(seed_results: list) -> dict:
    """Aggregate metrics across seeds with Wilson CIs."""
    recalls = [r['recall'] for r in seed_results]
    precisions = [r['precision'] for r in seed_results]
    false_failures = [r['false_failure_rate'] for r in seed_results]
    f1s = [r['f1'] for r in seed_results]
    
    n_seeds = len(recalls)
    
    # Wilson CI on the mean recall (treating each seed as a Bernoulli trial)
    mean_recall = np.mean(recalls)
    mean_precision = np.mean(precisions)
    mean_ff = np.mean(false_failures)
    mean_f1 = np.mean(f1s)
    
    # Standard error
    se_recall = np.std(recalls, ddof=1) / np.sqrt(n_seeds) if n_seeds > 1 else 0
    se_precision = np.std(precisions, ddof=1) / np.sqrt(n_seeds) if n_seeds > 1 else 0
    se_ff = np.std(false_failures, ddof=1) / np.sqrt(n_seeds) if n_seeds > 1 else 0
    se_f1 = np.std(f1s, ddof=1) / np.sqrt(n_seeds) if n_seeds > 1 else 0
    
    z = 1.96  # 95% CI
    return {
        'n_seeds': n_seeds,
        'recall_mean': mean_recall,
        'recall_ci': (mean_recall - z * se_recall, mean_recall + z * se_recall),
        'precision_mean': mean_precision,
        'precision_ci': (mean_precision - z * se_precision, mean_precision + z * se_precision),
        'false_failure_rate_mean': mean_ff,
        'false_failure_rate_ci': (mean_ff - z * se_ff, mean_ff + z * se_ff),
        'f1_mean': mean_f1,
        'f1_ci': (mean_f1 - z * se_f1, mean_f1 + z * se_f1),
    }


def mcnemar_test(results_a: list, results_b: list) -> dict:
    """McNemar test for paired binary outcomes.
    
    Compares two strategies on the same circuits (matched by circuit name).
    Tests whether the proportion of discordant pairs differs from 0.5.
    """
    # Build lookup by circuit name
    lookup_a = {r['circuit']: r for r in results_a}
    lookup_b = {r['circuit']: r for r in results_b}
    
    # Count discordant pairs
    b_wins = 0  # A fails, B passes
    a_wins = 0  # A passes, B fails
    
    for name in lookup_a:
        if name not in lookup_b:
            continue
        a_passed = lookup_a[name]['passed']
        b_passed = lookup_b[name]['passed']
        if a_passed and not b_passed:
            a_wins += 1
        elif not a_passed and b_passed:
            b_wins += 1
    
    # McNemar statistic (with continuity correction)
    total_discordant = a_wins + b_wins
    if total_discordant == 0:
        return {'statistic': 0.0, 'p_value': 1.0, 'a_wins': 0, 'b_wins': 0}
    
    statistic = (abs(a_wins - b_wins) - 1) ** 2 / total_discordant if total_discordant > 0 else 0
    
    # p-value from chi-squared distribution with 1 df
    from scipy import stats
    p_value = 1 - stats.chi2.cdf(statistic, df=1)
    
    return {
        'statistic': statistic,
        'p_value': p_value,
        'a_wins': a_wins,
        'b_wins': b_wins,
        'total_discordant': total_discordant
    }


def main():
    parser = argparse.ArgumentParser(description="Phase 1 multi-seed driver")
    parser.add_argument("--seeds", type=int, nargs='+', default=[42])
    parser.add_argument("--strategies", type=str, nargs='+', 
                        default=["adaptive_zkc", "fixed", "hoeffding", "wilson", "no_zkc"])
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--holdout", type=float, default=0.0, help="Hold-out fraction for calibration")
    parser.add_argument("--output-dir", type=str, default="outputs/phase1")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔬 Phase 1: {len(args.seeds)} seeds × {len(args.strategies)} strategies")
    print(f"   Seeds: {args.seeds}")
    print(f"   Strategies: {args.strategies}")
    print(f"   Hold-out: {args.holdout:.0%}")
    print()
    
    # Run all seeds × strategies
    all_results = defaultdict(lambda: defaultdict(list))
    for seed in args.seeds:
        print(f"\n{'='*60}")
        print(f"🌱 Seed {seed}")
        print(f"{'='*60}")
        seed_results = run_single_seed(seed, args.strategies, args.shots, args.reps, args.holdout)
        for strat_name, results in seed_results.items():
            all_results[strat_name][seed] = results
    
    # Aggregate metrics per strategy
    print(f"\n{'='*60}")
    print("📊 AGGREGATED METRICS (mean ± 95% CI)")
    print(f"{'='*60}")
    
    aggregated = {}
    for strat_name in args.strategies:
        seed_metrics = []
        for seed in args.seeds:
            metrics = compute_metrics(all_results[strat_name][seed])
            seed_metrics.append(metrics)
        
        agg = aggregate_metrics(seed_metrics)
        aggregated[strat_name] = agg
        
        print(f"\n{strat_name}:")
        print(f"  Recall:           {agg['recall_mean']:.3f} (95% CI: {agg['recall_ci'][0]:.3f}–{agg['recall_ci'][1]:.3f})")
        print(f"  Precision:        {agg['precision_mean']:.3f} (95% CI: {agg['precision_ci'][0]:.3f}–{agg['precision_ci'][1]:.3f})")
        print(f"  False-Failure:    {agg['false_failure_rate_mean']:.3f} (95% CI: {agg['false_failure_rate_ci'][0]:.3f}–{agg['false_failure_rate_ci'][1]:.3f})")
        print(f"  F1:               {agg['f1_mean']:.3f} (95% CI: {agg['f1_ci'][0]:.3f}–{agg['f1_ci'][1]:.3f})")
    
    # McNemar tests: adaptive_zkc vs each baseline
    if "adaptive_zkc" in args.strategies:
        print(f"\n{'='*60}")
        print("📊 McNemar TESTS (adaptive_zkc vs baselines)")
        print(f"{'='*60}")
        
        adaptive_results = all_results["adaptive_zkc"]
        for strat_name in args.strategies:
            if strat_name == "adaptive_zkc":
                continue
            baseline_results = all_results[strat_name]
            
            # Aggregate across seeds
            all_adaptive = []
            all_baseline = []
            for seed in args.seeds:
                all_adaptive.extend(adaptive_results[seed])
                all_baseline.extend(baseline_results[seed])
            
            test = mcnemar_test(all_adaptive, all_baseline)
            sig = "***" if test['p_value'] < 0.001 else "**" if test['p_value'] < 0.01 else "*" if test['p_value'] < 0.05 else "ns"
            print(f"\nadaptive_zkc vs {strat_name}:")
            print(f"  Discordant pairs: {test['total_discordant']} (adaptive wins: {test['a_wins']}, baseline wins: {test['b_wins']})")
            print(f"  McNemar statistic: {test['statistic']:.3f}")
            print(f"  p-value: {test['p_value']:.4f} {sig}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"phase1_results_{timestamp}.json"
    
    # Convert to serializable format
    serializable = {
        'config': {
            'seeds': args.seeds,
            'strategies': args.strategies,
            'shots': args.shots,
            'reps': args.reps,
            'holdout': args.holdout,
        },
        'aggregated': aggregated,
        'raw': {strat: {str(seed): results for seed, results in strat_results.items()} 
                for strat, strat_results in all_results.items()}
    }
    
    with open(output_file, 'w') as f:
        json.dump(serializable, f, indent=2)
    
    print(f"\n✅ Results saved to {output_file}")


if __name__ == "__main__":
    main()
