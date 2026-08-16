"""
Week 3 Integration Test: IBM Backend Execution
Run this after setting up IBM credentials:
  qiskit-runtime-service save --channel ibm_quantum --token <token>
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.qfa_verify.experiments.orchestrator import SafetyOrchestrator

def test_week3_simulator():
    """Test with simulator (no IBM credits used)"""
    print("WEEK 3: IBM Backend Integration (Simulator Mode)")
    print("="*60)
    
    orch = SafetyOrchestrator(backend="fake_brisbane", use_ibm=False)
    
    # Run subset for testing
    orch.run_full_suite(
        backends=['fake_brisbane'],
        shots=512,  # Reduced for speed
        reps=3      # Reduced for speed
    )

def test_week3_real_ibm():
    """Test on real IBM hardware (costs credits).

    NOTE: IBMRunner.execute_benchmark is currently a stub (returns []).
    Real-hardware execution requires implementing the IBM Runtime Sampler
    path — tracked as Phase 3 of the research roadmap.
    """
    print("WEEK 3: IBM Backend Integration (REAL HARDWARE)")
    print("⚠️  This will consume IBM Quantum credits!")
    print("⛔ Stub not implemented yet — see run_full_suite in SafetyOrchestrator.")

if __name__ == "__main__":
    # Default: run simulator
    test_week3_simulator()
