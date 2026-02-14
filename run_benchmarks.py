import json
import os
from qfa_verify.experiments.orchestrator import SafetyOrchestrator

def main():
    # use_ibm=False taaki local simulator chale
    orch = SafetyOrchestrator(backend="fake_brisbane", use_ibm=False)
    
    # Ye ek line 24 circuits chalayegi aur threshold "learn" karegi
    print("🚀 Running full adaptive suite...")
    orch.run_full_suite(backends=["fake_brisbane"])
    
    print("\n✅ Final report generated in outputs/experiments/final_report.json")

if __name__ == "__main__":
    main()
