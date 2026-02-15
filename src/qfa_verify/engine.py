import logging
import numpy as np
from qiskit import QuantumCircuit, transpile
# Absolute imports to prevent circularity
from src.qfa_verify.experiments.orchestrator import SafetyOrchestrator
from src.qfa_verify.ibm.runner import SimulatorRunner

class MetricStrategies:
    @staticmethod
    def probability(counts, target_state):
        total = sum(counts.values())
        return counts.get(target_state, 0) / total if total > 0 else 0

    @staticmethod
    def parity(counts, target_states):
        total = sum(counts.values())
        if isinstance(target_states, str):
            target_states = [target_states]
        success_count = sum(counts.get(s, 0) for s in target_states)
        return success_count / total if total > 0 else 0

    @staticmethod
    def expectation_z(counts, _=None):
        total = sum(counts.values())
        if total == 0: return 0
        expectation = 0
        for bitstring, count in counts.items():
            # Parity of 1s determines the eigenvalue (-1 or +1)
            parity = (-1) ** (bitstring.count('1'))
            expectation += parity * (count / total)
        # Map range [-1, 1] to [0, 1] for unified thresholding
        return (expectation + 1) / 2

class UniversalVerifier:
    def __init__(self, backend_name="fake_brisbane"):
        self.backend_name = backend_name
        self.orchestrator = SafetyOrchestrator(backend=backend_name)
        
        # Initialize runner and extract the actual backend object for transpilation
        self.runner = SimulatorRunner()
        self.backend_obj = self.runner.backends.get(backend_name, self.runner.backends['fake_brisbane'])
        
        # Setup Logger
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("UniversalVerifier")

    def _calibrate_noise_floor(self, target_qubits: list):
        """
        Phase 2: Zero-Knowledge Calibration (ZKC).
        Executes a Bell-state probe to measure real-time hardware fidelity.
        """
        self.logger.info(f"⚡ Running ZKC Probe on physical qubits {target_qubits[:2]}...")
        
        probe_qc = QuantumCircuit(2)
        probe_qc.h(0)
        probe_qc.cx(0, 1)
        probe_qc.measure_all()
        
        # Transpile to the physical location of the actual circuit
        t_probe = transpile(probe_qc, self.backend_obj, initial_layout=target_qubits[:2])
        
        from qiskit_aer import AerSimulator
        sim = AerSimulator.from_backend(self.backend_obj)
        job = sim.run(t_probe, shots=1024)
        counts = job.result().get_counts()
        
        cleaned_counts = {k.replace(" ", ""): v for k, v in counts.items()}
        fidelity = (cleaned_counts.get('00', 0) + cleaned_counts.get('11', 0)) / 1024
        loss = 1.0 - fidelity
        
        self.logger.info(f"📡 Probe Fidelity: {fidelity:.4f} | Measured Loss: {loss:.4f}")
        return loss

    def _calculate_adaptive_anchor(self, circuit, calibration_loss):
        """
        Industry-Standard Volume-Based Scaling.
        Calculates noise budget based on entangling gate count and register width.
        """
        # 1. Count total two-qubit gates (The primary noise drivers in NISQ)
        ops = circuit.count_ops()
        n_2q = sum(ops.get(gate, 0) for gate in ['cx', 'cz', 'ecr', 'ccx', 'cp'])
        
        # 2. Factor in the width (decoherence risk)
        width = circuit.num_qubits
        
        # 3. Calculate 'Effective Noise Volume'
        # Weighting 2-qubit gates as 10x more impactful than single qubits/width
        effective_volume = n_2q + (width * 0.1)
        
        # 4. Exponential Decay Formula: P_success = (1 - error_rate)^Volume
        error_rate = max(0.001, calibration_loss)
        # Use a 0.98 safety buffer to ensure 100% Recall for the Safety Anchor
        adaptive_threshold = ((1.0 - error_rate) ** effective_volume) * 0.98
        
        # 5. The Safety Floor (Prevents anchor from reaching 0)
        return max(0.10, adaptive_threshold)

    def verify(self, circuit, ltl_spec, metric_type="probability", target_params=None):
        """
        The Universal Verification Pipeline.
        """
        # 1. Transpile main circuit to target backend
        ready_circuit = transpile(circuit, self.backend_obj, optimization_level=3)

        # 2. Identify physical qubits for ZKC
        layout = ready_circuit.layout.final_index_layout()
        physical_qubits = layout if layout else [0, 1]

        # 3. Perform Calibration and Anchor Calculation
        cal_loss = self._calibrate_noise_floor(physical_qubits)
        threshold = self._calculate_adaptive_anchor(ready_circuit, cal_loss)

        # 4. Execute Custom Circuit via the Runner
        self.logger.info(f"🚀 Executing target circuit on {self.backend_name}...")
        results = self.runner.execute_benchmark(
            {"custom_circuit": ready_circuit}, 
            backend_name=self.backend_name
        )
        counts = results[0].counts

        # 5. Metric calculation and Adaptive Verdict
        metric_value = self._calculate_metric(counts, metric_type, target_params)
        verdict = "pass" if metric_value >= threshold else "fail"

        return {
            "verdict": verdict,
            "metric_value": metric_value,
            "threshold": threshold,
            "calibration_loss": cal_loss,
            "counts": counts
        }

    def _calculate_metric(self, counts, metric_type, target_params):
        cleaned_counts = {k.replace(" ", ""): v for k, v in counts.items()}
        strategies = {
            "probability": MetricStrategies.probability,
            "parity": MetricStrategies.parity,
            "expectation": MetricStrategies.expectation_z
        }
        return strategies[metric_type](cleaned_counts, target_params)
