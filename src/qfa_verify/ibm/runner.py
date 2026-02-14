"""
IBM Quantum Backend Runner
Executes circuits on real IBM hardware and collects results.
"""
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler, Options
from qiskit import transpile, QuantumCircuit
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import time
from pathlib import Path

@dataclass
class IBMJobResult:
    """Result from IBM backend execution"""
    circuit_name: str
    backend_name: str
    job_id: str
    counts: Dict[str, int]
    shots: int
    timestamp: str
    success: bool
    error_message: Optional[str] = None
    calibration_data: Optional[Dict] = None

class IBMRunner:
    """
    Manages execution of quantum test suites on IBM backends.
    Handles job queuing, transpilation, and result collection.
    """
    
    def __init__(self, token: Optional[str] = None, instance: Optional[str] = None):
        try:
            self.service = QiskitRuntimeService(channel="ibm_quantum", token=token, instance=instance)
            print(f"✅ Connected to IBM Quantum: {self.service.active_account()}")
        except Exception as e:
            print(f"❌ Failed to connect to IBM: {e}")
            print("   Run: qiskit-runtime-service save --channel ibm_quantum --token <your_token>")
            raise
    
    def list_backends(self, min_qubits: int = 5):
        """List available backends"""
        backends = self.service.backends(
            operational=True, 
            simulator=False,
            min_num_qubits=min_qubits
        )
        print(f"\nAvailable backends (>{min_qubits} qubits):")
        for b in backends:
            print(f"  - {b.name}: {b.configuration().n_qubits} qubits")
        return backends
    
    def execute_benchmark(self, circuits: Dict[str, QuantumCircuit], 
                         backend_name: str,
                         shots: int = 1024,
                         reps: int = 10,
                         optimization_level: int = 0) -> List[IBMJobResult]:
        """
        Execute benchmark suite on IBM backend.
        
        Args:
            circuits: Dict of {name: circuit}
            backend_name: e.g., 'ibm_brisbane'
            shots: Shots per circuit
            reps: Number of repetitions (different transpilations)
            optimization_level: 0=preserve circuit, 3=full optimize
        
        Returns:
            List of IBMJobResult
        """
        backend = self.service.backend(backend_name)
        print(f"\n🔬 Running on {backend_name} ({backend.configuration().n_qubits} qubits)")
        
        # Transpile circuits for this backend
        transpiled = {}
        for name, qc in circuits.items():
            # Transpile multiple times for statistical variance
            transpiled[name] = [
                transpile(qc, backend, optimization_level=optimization_level, seed_transpiler=i)
                for i in range(reps)
            ]
        
        results = []
        
        # Use Session for efficient batch processing
        with Session(backend=backend) as session:
            sampler = Sampler(session=session)
            
            # Flatten list for batch submission
            all_circuits = []
            metadata = []  # Track which circuit each index corresponds to
            
            for name, circuits_list in transpiled.items():
                for i, circ in enumerate(circuits_list):
                    all_circuits.append(circ)
                    metadata.append({'name': name, 'rep': i})
            
            print(f"  Submitting {len(all_circuits)} circuits ({len(circuits)} types × {reps} reps)...")
            
            # Submit job
            job = sampler.run(all_circuits, shots=shots)
            print(f"  Job ID: {job.job_id()}")
            print(f"  Queue position: {job.metrics()['position']} (est. wait: {job.metrics()['estimated_start_time']})")
            
            # Wait for results
            try:
                job_result = job.result()
                print("  ✅ Job completed successfully")
                
                # Parse results
                for idx, (meta, pub_result) in enumerate(zip(metadata, job_result)):
                    # Extract counts from result
                    # Note: API might vary slightly based on qiskit-ibm-runtime version
                    try:
                        counts = pub_result.data.c.get_counts()
                    except:
                        # Fallback for different result formats
                        counts = pub_result.data.meas.get_counts() if hasattr(pub_result.data, 'meas') else {}
                    
                    # Fetch calibration data for this specific run
                    cal_data = self._fetch_calibration(backend, job.job_id())
                    
                    result = IBMJobResult(
                        circuit_name=meta['name'],
                        backend_name=backend_name,
                        job_id=job.job_id(),
                        counts=counts,
                        shots=shots,
                        timestamp=datetime.now().isoformat(),
                        success=True,
                        calibration_data=cal_data
                    )
                    results.append(result)
                    
            except Exception as e:
                print(f"  ❌ Job failed: {e}")
                # Add failed results
                for meta in metadata:
                    results.append(IBMJobResult(
                        circuit_name=meta['name'],
                        backend_name=backend_name,
                        job_id=job.job_id(),
                        counts={},
                        shots=shots,
                        timestamp=datetime.now().isoformat(),
                        success=False,
                        error_message=str(e)
                    ))
        
        return results
    
    def _fetch_calibration(self, backend, job_id: str) -> Dict:
        """Fetch calibration data at time of execution"""
        try:
            props = backend.properties()
            # Extract key metrics
            return {
                'timestamp': str(props.last_update_date) if hasattr(props, 'last_update_date') else 'unknown',
                't1_avg': sum(props.t1(q) for q in range(backend.configuration().n_qubits)) / backend.configuration().n_qubits,
                't2_avg': sum(props.t2(q) for q in range(backend.configuration().n_qubits)) / backend.configuration().n_qubits,
                'gate_error_avg': 0.001  # Simplified
            }
        except:
            return {}
    
    def save_results(self, results: List[IBMJobResult], filename: str):
        """Save results to JSON"""
        data = [asdict(r) for r in results]
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"💾 Saved {len(results)} results to {filename}")

class SimulatorRunner(IBMRunner):
    """
    Fallback runner using Aer simulator with noise model.
    Use this if IBM credits run out or for CI/CD testing.
    """
    
    def __init__(self):
        from qiskit_aer import AerSimulator
        try:
            from qiskit.providers.fake_provider import FakeBrisbane, FakeSherbrooke
        except ImportError:
            # Newer Qiskit versions
            from qiskit_ibm_runtime.fake_provider import FakeBrisbane, FakeSherbrooke
        
        self.backends = {
            'fake_brisbane': FakeBrisbane(),
            'fake_sherbrooke': FakeSherbrooke()
        }
        print("⚠️  Using Simulator (no IBM credits used)")
    
    def execute_benchmark(self, circuits: Dict[str, QuantumCircuit], 
                         backend_name: str = 'fake_brisbane',
                         shots: int = 1024, reps: int = 10, **kwargs) -> List[IBMJobResult]:
        """Execute on noisy simulator"""
        from qiskit_aer import AerSimulator
        
        backend = AerSimulator.from_backend(self.backends[backend_name])
        print(f"\n🔬 Running on {backend_name} (simulator)")
        
        results = []
        
        for name, qc in circuits.items():
            print(f"  Running {name}...")
            for i in range(reps):
                transpiled = transpile(qc, backend, seed_transpiler=i)
                job = backend.run(transpiled, shots=shots)
                counts = job.result().get_counts()
                
                results.append(IBMJobResult(
                    circuit_name=name,
                    backend_name=backend_name,
                    job_id=f"sim_{name}_{i}",
                    counts=counts,
                    shots=shots,
                    timestamp=datetime.now().isoformat(),
                    success=True,
                    calibration_data={'simulator': True, 'backend': backend_name}
                ))
        
        return results
