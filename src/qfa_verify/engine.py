import logging
import numpy as np
import random
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import XGate, ZGate, YGate
# Absolute imports to prevent circularity
from src.qfa_verify.experiments.orchestrator import SafetyOrchestrator
from src.qfa_verify.ibm.runner import SimulatorRunner
from src.qfa_verify.ltl.parser import parse_ltl

class MetricStrategies:
    @staticmethod
    def probability(counts, target_state):
        total = sum(counts.values())
        # Strip potential spaces from target string
        target = target_state.replace(" ", "") if target_state else ""
        return counts.get(target, 0) / total if total > 0 else 0

    @staticmethod
    def parity(counts, target_states):
        total = sum(counts.values())
        if isinstance(target_states, str):
            target_states = [target_states]
        
        # Clean the target strings (e.g., "00, 11" -> ["00", "11"])
        clean_targets = [s.replace(" ", "") for s in target_states]
        success_count = sum(counts.get(s, 0) for s in clean_targets)
        return success_count / total if total > 0 else 0

    @staticmethod
    def expectation_z(counts, _=None):
        total = sum(counts.values())
        if total == 0: return 0
        expectation = 0
        for bitstring, count in counts.items():
            # Parity of 1s determines the eigenvalue (-1 or +1)
            # Bitstring keys in counts are already cleaned by the caller
            parity = (-1) ** (bitstring.count('1'))
            expectation += parity * (count / total)
        return (expectation + 1) / 2

class AdversarialNoise:
    """
    Injects controlled stochastic noise into the circuit
    to stress-test the Adaptive Safety Anchor.
    """
    @staticmethod
    def inject_gate_errors(circuit, error_probability=0.05):
        if error_probability <= 0:
            return circuit
        # Build a new circuit with same number of qubits/clbits to avoid qreg/creg constructor differences
        try:
            nq = circuit.num_qubits
            nc = circuit.num_clbits
        except Exception:
            # Fallback to register-based reconstruction
            noisy_qc = QuantumCircuit(*circuit.qregs, *circuit.cregs)
            for instruction in circuit.data:
                noisy_qc.append(instruction)
                if random.random() < error_probability:
                    target_qubit = instruction.qubits[0]
                    error_gate = XGate() if random.random() > 0.5 else ZGate()
                    noisy_qc.append(error_gate, [target_qubit])
            return noisy_qc

        noisy_qc = QuantumCircuit(nq, nc)
        for instruction in circuit.data:
            noisy_qc.append(instruction)
            if instruction.operation.name == 'measure':
                continue
            if random.random() < error_probability:
                target_qubit = instruction.qubits[0]
                error_gate = random.choice([XGate(), YGate(), ZGate()])
                noisy_qc.append(error_gate, [target_qubit])
        
        return noisy_qc

class UniversalVerifier:
    def __init__(self, backend_name="fake_brisbane", seed=None):
        self.backend_name = backend_name
        self.seed = seed
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        self.orchestrator = SafetyOrchestrator(backend=backend_name)
        self.runner = SimulatorRunner(seed=seed)
        self.backend_obj = self.runner.backends.get(backend_name, self.runner.backends['fake_brisbane'])
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("UniversalVerifier")

    def _parse_spec(self, ltl_spec: str) -> dict:
        """Parse and validate the LTL spec. Raises on invalid syntax."""
        return parse_ltl(ltl_spec)

    def _spec_to_target(self, parsed_spec: dict, metric_type: str):
        """
        Derive the metric target(s) from the LTL predicate.
        The spec is authoritative: prob(|b1> + |b2> > t) maps to
        a parity-style sum over the listed basis states.
        """
        pred = parsed_spec['predicate']
        bases = pred.get('bases') or ([pred['basis']] if pred.get('basis') else [])
        if metric_type == 'parity':
            return bases
        return bases[0] if bases else None

    def _spec_direction(self, parsed_spec: dict) -> str:
        """Verdict direction: '>' means pass when metric exceeds threshold; '<' means the inverse."""
        return parsed_spec['predicate'].get('comparison', '>')

    def _calibrate_noise_floor(self, target_qubits: list):
        """Phase 2: Zero-Knowledge Calibration (ZKC)."""
        self.logger.info(f"⚡ Running ZKC Probe on physical qubits {target_qubits[:2]}...")
        
        probe_qc = QuantumCircuit(2)
        probe_qc.h(0)
        probe_qc.cx(0, 1)
        probe_qc.measure_all()
        
        t_probe = transpile(probe_qc, self.backend_obj, initial_layout=target_qubits[:2])
        
        from qiskit_aer import AerSimulator
        sim = AerSimulator.from_backend(self.backend_obj)
        if self.seed is not None:
            sim.set_options(seed_simulator=self.seed)
        # 4096 shots for research-grade stability
        job = sim.run(t_probe, shots=4096)
        counts = job.result().get_counts()
        
        cleaned_counts = {k.replace(" ", ""): v for k, v in counts.items()}
        fidelity = (cleaned_counts.get('00', 0) + cleaned_counts.get('11', 0)) / 4096
        loss = 1.0 - fidelity
        
        self.logger.info(f"📡 Probe Fidelity: {fidelity:.4f} | Measured Loss: {loss:.4f}")
        return loss

    def _calculate_adaptive_anchor(self, circuit, calibration_loss):
        """Industry-Standard Volume-Based Scaling."""
        from src.qfa_verify.thresholds import count_2q_gates
        n_2q = count_2q_gates(circuit)
        width = circuit.num_qubits
        
        effective_volume = n_2q + (width * 0.1)
        error_rate = max(0.001, calibration_loss)
        adaptive_threshold = ((1.0 - error_rate) ** effective_volume) * 0.98
        
        return max(0.10, adaptive_threshold)

    def verify(self, circuit, ltl_spec, metric_type="probability", target_params=None, adversarial_noise=0.0):
        """The Universal Verification Pipeline.

        The LTL spec is now authoritative: it supplies the target basis state(s)
        and the comparison direction for the verdict. Explicit --target CLI
        parameters remain as an override for multi-target parity checks.
        """
        # 1. Parse the temporal spec up front (fail fast on invalid LTL).
        parsed_spec = self._parse_spec(ltl_spec)
        direction = self._spec_direction(parsed_spec)

        ready_circuit = transpile(circuit, self.backend_obj, optimization_level=3)
        layout = ready_circuit.layout.final_index_layout()
        physical_qubits = layout if layout else [0, 1]

        cal_loss = self._calibrate_noise_floor(physical_qubits)
        threshold = self._calculate_adaptive_anchor(ready_circuit, cal_loss)

        if adversarial_noise > 0:
            self.logger.warning(f"⚠️ Injecting {adversarial_noise*100}% Adversarial Noise...")
            ready_circuit = AdversarialNoise.inject_gate_errors(ready_circuit, adversarial_noise)

        self.logger.info(f"🚀 Executing target circuit on {self.backend_name}...")
        results = self.runner.execute_benchmark(
            {"custom_circuit": ready_circuit}, 
            backend_name=self.backend_name
        )
        counts = results[0].counts

        # Target derivation: spec wins unless the caller explicitly overrode it.
        spec_target = self._spec_to_target(parsed_spec, metric_type)
        effective_target = target_params if target_params is not None else spec_target
        metric_value = self._calculate_metric(counts, metric_type, effective_target)

        if direction == '<' or direction == '<=':
            verdict = "pass" if metric_value <= threshold else "fail"
        else:
            verdict = "pass" if metric_value >= threshold else "fail"

        return {
            "verdict": verdict,
            "metric_value": metric_value,
            "threshold": threshold,
            "calibration_loss": cal_loss,
            "adversarial_noise": adversarial_noise,
            "spec": ltl_spec,
            "spec_parsed": parsed_spec,
            "counts": counts
        }

    def _calculate_metric(self, counts, metric_type, target_params):
        # Clean counts once before passing to strategies
        cleaned_counts = {k.replace(" ", ""): v for k, v in counts.items()}
        strategies = {
            "probability": MetricStrategies.probability,
            "parity": MetricStrategies.parity,
            "expectation": MetricStrategies.expectation_z
        }
        return strategies[metric_type](cleaned_counts, target_params)
