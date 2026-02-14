from .experiments.orchestrator import SafetyOrchestrator
from .qfa.product_construction import ProductAutomaton

__version__ = "0.1.0"

def verify(circuit, spec, backend):
    """One-line entry point for developers."""
    orch = SafetyOrchestrator(backend)
    return orch.run_full_stack(circuit, spec)
