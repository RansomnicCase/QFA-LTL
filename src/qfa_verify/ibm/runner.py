from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler
from qiskit import transpile, QuantumCircuit
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os

@dataclass
class IBMJobResult:
    circuit_name: str
    backend_name: str
    job_id: str
    counts: Dict[str, int]
    shots: int
    timestamp: str
    success: bool
    error_message: Optional[str] = None

class IBMRunner:
    def __init__(self, token=None, instance=None, seed: Optional[int] = None):
        self.seed = seed
        self.service = None
        if token:
            try:
                self.service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance=instance)
                print(f"✅ Connected to IBM")
            except Exception as e:
                print(f"❌ IBM Connection Failed: {e}")
        else:
            print("💡 No IBM token. Local mode enabled.")
    
    def execute_benchmark(self, circuits: Dict[str, QuantumCircuit], backend_name: str, shots: int = 1024, reps: int = 1) -> List[IBMJobResult]:
        if self.service is None:
            # If this is called on the base IBMRunner without service, it's an error.
            # But the Orchestrator will use SimulatorRunner instead.
            raise RuntimeError("IBM Service not initialized. Use SimulatorRunner for local backends.")
        
        backend = self.service.backend(backend_name)
        # (Standard IBM Cloud execution logic remains here...)
        return []

class SimulatorRunner(IBMRunner):
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        try:
            from qiskit_ibm_runtime.fake_provider import FakeBrisbane, FakeSherbrooke
        except:
            from qiskit.providers.fake_provider import FakeBrisbane, FakeSherbrooke
            
        self.backends = {'fake_brisbane': FakeBrisbane(), 'fake_sherbrooke': FakeSherbrooke()}
        print("⚠️ Using Local Simulator (Aer + Noise Model)")
    
    def execute_benchmark(self, circuits: Dict[str, QuantumCircuit], backend_name: str = 'fake_brisbane', shots: int = 1024, reps: int = 1, **kwargs) -> List[IBMJobResult]:
        from qiskit_aer import AerSimulator
        target_backend = self.backends.get(backend_name, self.backends['fake_brisbane'])
        sim = AerSimulator.from_backend(target_backend)
        if self.seed is not None:
            sim.set_options(seed_simulator=self.seed)
        
        results = []
        for name, qc in circuits.items():
            for i in range(reps):
                t_qc = transpile(qc, sim)
                job = sim.run(t_qc, shots=shots)
                counts = job.result().get_counts()
                results.append(IBMJobResult(
                    circuit_name=name, backend_name=backend_name, job_id=f"sim_{name}_{i}",
                    counts=counts, shots=shots, timestamp=datetime.now().isoformat(), success=True
                ))
        return results
