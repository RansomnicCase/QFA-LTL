import argparse
from qfa_verify.experiments.orchestrator import SafetyOrchestrator

def main():
    parser = argparse.ArgumentParser(description="QFA-LTL benchmark suite runner")
    parser.add_argument("--backend", default="fake_brisbane")
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible runs")
    args = parser.parse_args()

    orch = SafetyOrchestrator(backend=args.backend, use_ibm=False, seed=args.seed)

    print(f"🚀 Running full adaptive suite (seed={args.seed})...")
    orch.run_full_suite(backends=[args.backend], shots=args.shots, reps=args.reps)

    print("\n✅ Final report generated in outputs/experiments/")

if __name__ == "__main__":
    main()
