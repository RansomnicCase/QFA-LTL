# src/qfa_verify/__init__.py

from .experiments.orchestrator import SafetyOrchestrator
from .qfa.product_construction import ProductAutomaton

__version__ = "0.1.0"

def verify(circuit, spec, backend=None):
    """
    High-level API for the QFA-LTL framework.
    
    Args:
        circuit: Qiskit QuantumCircuit to verify.
        spec: LTL string specification.
        backend: Qiskit backend or noise model.
    """
    orch = SafetyOrchestrator(backend)
    # Ensure this method name matches what is in your orchestrator.py
    return orch.run_full_stack(circuit, spec)
