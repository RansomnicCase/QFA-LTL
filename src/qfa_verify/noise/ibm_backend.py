"""
IBM Quantum Backend Integration
Fetches calibration data and computes noise-aware thresholds.
"""
try:
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit import QuantumCircuit
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class NoiseProfile:
    """Complete noise characterization for a backend"""
    t1_times: Dict[int, float]
    t2_times: Dict[int, float]
    gate_errors: Dict[Tuple[int, ...], float]
    readout_errors: Dict[int, float]
    timestamp: str
    backend_name: str

class IBMNoiseFetcher:
    """Fetches and processes IBM backend noise data"""
    
    def __init__(self, token: Optional[str] = None, instance: Optional[str] = None):
        if not QISKIT_AVAILABLE:
            print("Warning: Qiskit not available, using simulated noise")
            self.service = None
            return
            
        try:
            self.service = QiskitRuntimeService(channel="ibm_quantum", token=token, instance=instance)
        except Exception as e:
            print(f"Warning: Could not initialize IBM service: {e}")
            self.service = None
    
    def get_noise_profile(self, backend_name: str) -> Optional[NoiseProfile]:
        """Fetch comprehensive noise profile from IBM"""
        if not self.service:
            return self._simulated_noise_profile(backend_name)
            
        try:
            backend = self.service.backend(backend_name)
            props = backend.properties()
            config = backend.configuration()
            
            t1 = {}
            t2 = {}
            ro_errors = {}
            
            # Parse qubit properties (handle different Qiskit versions)
            for qubit_idx in range(config.n_qubits):
                try:
                    # Try different property access patterns
                    qubit_props = props.qubit_property(qubit_idx)
                    
                    # Handle both list and dict formats
                    if isinstance(qubit_props, dict):
                        t1[qubit_idx] = qubit_props.get('T1', 100.0)
                        t2[qubit_idx] = qubit_props.get('T2', 100.0)
                        ro_errors[qubit_idx] = qubit_props.get('readout_error', 0.01)
                    else:
                        # List format: [(name, value, unit), ...]
                        for prop in qubit_props:
                            if prop[0] == 'T1':
                                t1[qubit_idx] = prop[1]
                            elif prop[0] == 'T2':
                                t2[qubit_idx] = prop[1]
                            elif prop[0] == 'readout_error':
                                ro_errors[qubit_idx] = prop[1]
                                
                except Exception:
                    # Use defaults
                    t1[qubit_idx] = 100.0
                    t2[qubit_idx] = 100.0
                    ro_errors[qubit_idx] = 0.01
            
            # Parse gate errors
            gate_errs = {}
            if hasattr(props, 'gates'):
                for gate in props.gates:
                    qubits = tuple(gate.qubits)
                    # Find gate_error in parameters
                    gate_error = 0.001  # default
                    if hasattr(gate, 'parameters'):
                        for param in gate.parameters:
                            if hasattr(param, 'name') and param.name == 'gate_error':
                                gate_error = param.value
                                break
                    gate_errs[qubits] = gate_error
            
            from datetime import datetime
            return NoiseProfile(
                t1_times=t1,
                t2_times=t2,
                gate_errors=gate_errs,
                readout_errors=ro_errors,
                timestamp=str(datetime.now()),
                backend_name=backend_name
            )
            
        except Exception as e:
            print(f"Error fetching noise profile: {e}")
            return self._simulated_noise_profile(backend_name)
    
    def _simulated_noise_profile(self, backend_name: str) -> NoiseProfile:
        """Generate realistic fake noise profile for testing"""
        print(f"Using simulated noise profile for {backend_name}")
        return NoiseProfile(
            t1_times={i: 100.0 + np.random.normal(0, 10) for i in range(127)},
            t2_times={i: 100.0 + np.random.normal(0, 10) for i in range(127)},
            gate_errors={(i,): 0.001 for i in range(127)},
            readout_errors={i: 0.01 for i in range(127)},
            timestamp="simulated",
            backend_name=backend_name
        )
    
    def calculate_circuit_noise(self, qc, profile: NoiseProfile) -> float:
        """Calculate aggregate circuit noise from gate errors"""
        if not hasattr(qc, 'data'):
            return 0.05  # default 5%
            
        total_error = 0.0
        
        for instr in qc.data:
            qubits = tuple(q.index for q in instr.qubits)
            gate_error = profile.gate_errors.get(qubits, 0.001)
            total_error += gate_error
        
        for qubit in range(qc.num_qubits):
            total_error += profile.readout_errors.get(qubit, 0.01)
        
        return min(total_error, 0.5)

class NoiseAwareThresholdCalculator:
    """Calculates dynamic test thresholds accounting for hardware noise"""
    
    def __init__(self, confidence: float = 0.95):
        self.confidence = confidence
        self.z_score = 1.96
    
    def calculate(self, ideal_prob: float, hardware_noise: float, 
                  num_shots: int = 1024, safety_factor: float = 1.0) -> Dict:
        """Calculate final test threshold"""
        p = ideal_prob
        n = num_shots
        
        # Wilson score lower bound (more accurate for proportions)
        z = self.z_score
        if n <= 0:
            wilson_margin = 0.0
        else:
            denom = 1 + (z**2)/n
            center = p + (z**2)/(2*n)
            sq = p * (1 - p) / n + (z**2) / (4 * n**2)
            lower = (center - z * np.sqrt(max(sq, 0))) / denom
            wilson_margin = max(0.0, p - lower)
        
        # Hardware noise margin
        noise_margin = hardware_noise * ideal_prob * safety_factor
        
        # Conservative threshold
        threshold = max(0.0, ideal_prob - noise_margin - wilson_margin)
        
        return {
            'final_threshold': threshold,
            'ideal_probability': ideal_prob,
            'hardware_noise_margin': noise_margin,
            'statistical_margin': wilson_margin,
            'confidence_level': self.confidence,
            'formula': f"{ideal_prob:.3f} - {noise_margin:.3f} (noise) - {wilson_margin:.3f} (stat)"
        }
