import json
import os
from datetime import datetime
from qfa_verify.experiments.orchestrator import SafetyOrchestrator
from qfa_verify.experiments.benchmarks import BenchmarkSuite

def main():
    # Force use_ibm=False to ensure we use SimulatorRunner locally
    orch = SafetyOrchestrator(backend="fake_brisbane", use_ibm=False)
    suite = BenchmarkSuite()
    results = []

    print(f"🚀 Initializing Benchmark Suite...")
    print(f"📊 Targets: {len(suite.circuits)} circuits | Backend: fake_brisbane")

    for item in suite.circuits:
        print(f"Verifying {item['name']} ({item['type']})...", end=" ", flush=True)
        outcome = orch.run_full_stack(item['circuit'], item['ltl_spec'])
        
        results.append({
            "algorithm": item['name'],
            "type": item['type'],
            "pass_rate": outcome['pass_rate'] * 100,
            "verdict": outcome['verdict'],
            "threshold": outcome['threshold']
        })
        print(f"[{outcome['verdict'].upper()}]")

    report = {
        "backend": "fake_brisbane",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": results
    }

    report_path = "outputs/experiments/final_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)

    print(f"\n✅ Done! Data saved to {report_path}")

if __name__ == "__main__":
    main()
