"""
Week 3 Integration Test: IBM Backend Execution
Run this after setting up IBM credentials:
  qiskit-runtime-service save --channel ibm_quantum --token <token>
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.experiments.orchestrator import ExperimentOrchestrator

def test_week3_simulator():
    """Test with simulator (no IBM credits used)"""
    print("WEEK 3: IBM Backend Integration (Simulator Mode)")
    print("="*60)
    
    orch = ExperimentOrchestrator(use_ibm=False)
    
    # Run subset for testing
    orch.run_full_suite(
        backends=['fake_brisbane'],
        shots=512,  # Reduced for speed
        reps=3      # Reduced for speed
    )

def test_week3_real_ibm():
    """Test on real IBM hardware (costs credits)"""
    print("WEEK 3: IBM Backend Integration (REAL HARDWARE)")
    print("⚠️  This will consume IBM Quantum credits!")
    print("="*60)
    
    confirm = input("Do you want to run on real IBM hardware? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Aborted. Run test_week3_simulator() instead.")
        return
    
    orch = ExperimentOrchestrator(use_ibm=True)
    
    # List available backends
    orch.runner.list_backends(min_qubits=7)
    
    # Run on real backends
    orch.run_full_suite(
        backends=['ibm_brisbane', 'ibm_sherbrooke'],  # Choose 2-3
        shots=1024,
        reps=5  # 5 repetitions for statistical significance
    )

if __name__ == "__main__":
    # Default: run simulator
    test_week3_simulator()
    
    # Uncomment for real hardware:
    # test_week3_real_ibm()
