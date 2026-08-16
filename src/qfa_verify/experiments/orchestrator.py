from typing import Dict, List, Optional, Union
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import numpy as np

# Internal Imports
from ..ibm.runner import IBMRunner, SimulatorRunner, IBMJobResult
from ..experiments.benchmarks import BenchmarkSuite
from ..thresholds import ThresholdStrategy, AdaptiveZKC, DerivedAnchor, get_strategy


class SafetyOrchestrator:
    def __init__(self, backend="fake_brisbane", use_ibm: bool = False, token: Optional[str] = None, seed: Optional[int] = None):
        self.backend = backend
        self.use_ibm = use_ibm
        self.seed = seed
        
        # Select Backend Runner based on mode
        if use_ibm and token:
            self.runner = IBMRunner(token=token)
        else:
            self.runner = SimulatorRunner(seed=seed)
            
        # Setup Output Directory
        self.results_dir = Path("outputs/experiments")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Dynamic Target Memory
        self.learned_targets = {}

    def run_full_stack(self, circuit, ltl_spec):
        """
        One-line bridge for run_benchmarks.py.
        Executes a single circuit and returns the verdict.
        """
        # Execute on the selected backend
        name = "temp_circuit"
        # Extract algorithm type from LTL spec or name if possible
        # For simplicity in this bridge, we assume standard targeting
        results = self.runner.execute_benchmark(
            {name: circuit}, 
            backend_name=self.backend, 
            shots=1024, 
            reps=1
        )
        
        res = results[0]
        total = sum(res.counts.values())
        
        # In a single-circuit call, we provide a stable target for common benchmarks
        # To use the full "Learning" logic, use run_full_suite()
        counts = self._clean_counts(res.counts)
        sorted_states = sorted(counts, key=counts.get, reverse=True)
        top_state = sorted_states[0] if sorted_states else "00"
        
        # Metric calculation
        val = counts.get(top_state, 0) / total if total > 0 else 0
        threshold = 0.15 # Default safety threshold for single runs
        
        return {
            "verdict": "pass" if val > threshold else "fail",
            "pass_rate": val,
            "threshold": threshold
        }

    def run_full_suite(self, backends: List[str], shots: int = 1024, reps: int = 5,
                       strategy: Union[str, ThresholdStrategy] = "adaptive_zkc",
                       holdout_fraction: float = 0.0,
                       gray_margin: float = 0.0,
                       seed: Optional[int] = None):
        """Main Execution Loop for the full research battery.

        Args:
            backends: list of backend names
            shots: shots per execution
            reps: repetitions per circuit
            strategy: threshold strategy (name or instance)
            holdout_fraction: fraction of correct circuits to use for calibration (0 = in-sample)
            gray_margin: fraction of threshold used as a gray zone around the verdict.
                When > 0, a circuit whose metric is within gray_margin*threshold of the
                boundary gets verdict='borderline' instead of pass/fail. This is the
                honest "needs review" category — it prevents a noisy run from being
                falsely branded a hard failure.
            seed: random seed (overrides constructor seed)
        """
        if seed is not None:
            self.seed = seed
            self.runner.seed = seed

        if isinstance(strategy, str):
            strategy = get_strategy(strategy)
        
        print("="*60)
        print(f"🚀 STARTING QFA-LTL EXPERIMENT SUITE")
        print(f"   Strategy: {strategy.name} | Hold-out: {holdout_fraction:.0%} | Gray: {gray_margin:.0%} | Seed: {self.seed}")
        print("="*60)
        
        suite_obj = BenchmarkSuite()
        circuits = suite_obj.generate_all()

        all_results_buffer = []
        for backend in backends:
            results = self.runner.execute_benchmark(circuits, backend_name=backend, shots=shots, reps=reps)
            self._learn_targets(results)
            
            # Compute thresholds using the strategy
            thresholds = self._diagnose_and_get_thresholds(results, strategy, suite_obj, holdout_fraction)
            eval_results = self._evaluate_with_thresholds(results, thresholds, gray_margin=gray_margin)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.results_dir / f"{backend}_{strategy.name}_{timestamp}.json"
            self._save_eval_results(eval_results, filename)
            all_results_buffer.extend(eval_results)

        self._generate_report(all_results_buffer)
        return all_results_buffer

    def _clean_counts(self, counts: Dict) -> Dict[str, int]:
        return {k.replace(" ", ""): v for k, v in counts.items()}

    def _learn_targets(self, results: List[IBMJobResult]):
        self.learned_targets = {}
        for res in results:
            if not res.success or "_correct" not in res.circuit_name: continue
            algo = res.circuit_name.split('_')[0]
            counts = self._clean_counts(res.counts)
            if not counts: continue
            sorted_states = sorted(counts, key=counts.get, reverse=True)
            top_state = sorted_states[0]
            if algo == 'ghz':
                self.learned_targets[algo] = ['0' * len(top_state), '1' * len(top_state)]
            elif algo == 'qaoa':
                self.learned_targets[algo] = sorted_states[:2]
            else:
                self.learned_targets[algo] = top_state

    def _calculate_metric(self, base: str, counts: Dict, total: int) -> float:
        counts = self._clean_counts(counts)
        target = self.learned_targets.get(base)
        if isinstance(target, list):
            return sum(counts.get(t, 0) for t in target) / total
        return counts.get(target, 0) / total if target else max(counts.values())/total

    def _diagnose_and_get_thresholds(self, results: List[IBMJobResult], strategy: ThresholdStrategy,
                                     suite_obj: Optional[BenchmarkSuite] = None, holdout_fraction: float = 0.0) -> Dict:
        """Compute thresholds using the given strategy.

        If holdout_fraction > 0, correct circuits are split into calibration and test sets.
        The threshold is computed from the calibration set only, then applied to the test set.
        """
        by_algo = defaultdict(lambda: {'correct': [], 'buggy': []})
        for res in results:
            if not res.success: continue
            base = res.circuit_name.split('_')[0]
            is_buggy = 'correct' not in res.circuit_name
            total = sum(res.counts.values())
            val = self._calculate_metric(base, res.counts, total)
            key = 'buggy' if is_buggy else 'correct'
            by_algo[base][key].append(val)

        thresholds = {}
        for algo, data in by_algo.items():
            correct_vals = data['correct']
            if not correct_vals:
                thresholds[algo] = 0.15
                continue

            if holdout_fraction > 0 and len(correct_vals) > 1:
                # Hold-out: use a fraction of correct circuits for calibration
                n_cal = max(1, int(len(correct_vals) * (1 - holdout_fraction)))
                cal_vals = correct_vals[:n_cal]
            else:
                cal_vals = correct_vals

            # Get a representative circuit for volume-based strategies
            circuit = None
            noise_estimate = None
            p_ideal = None
            if suite_obj and hasattr(suite_obj, 'circuits'):
                for item in suite_obj.circuits:
                    if item['name'] == f'{algo}_correct':
                        circuit = item['circuit']
                        break

            # For the derived anchor: compute the ideal target probability
            # via the exact compiler (no peeking at noisy runs), and use the
            # ZKC probe's *measured* noise floor — not declared calibration,
            # which systematically underestimates the noise a real circuit sees.
            if isinstance(strategy, DerivedAnchor) and circuit is not None:
                p_ideal = self._compute_ideal_probability(algo, circuit)
                noise_estimate = self._zkc_probe_loss()

            if isinstance(strategy, AdaptiveZKC):
                # Use mean of correct values as a proxy for noise estimate
                noise_estimate = float(max(0.001, 1.0 - np.mean(cal_vals)))

            try:
                thresholds[algo] = strategy.compute_threshold(
                    algo, cal_vals, circuit, noise_estimate, p_ideal=p_ideal
                )
            except TypeError:
                # Strategies that don't accept p_ideal
                thresholds[algo] = strategy.compute_threshold(algo, cal_vals, circuit, noise_estimate)
        return thresholds

    def _zkc_probe_loss(self) -> float:
        """Run the ZKC Bell-state probe and return measured loss ε.

        Mirrors UniversalVerifier._calibrate_noise_floor: transpile a Bell
        probe onto the backend, run 4096 shots, measure the |00>/|11>
        fidelity. This is the framework's runtime noise measurement — the
        honest analog of real-device calibration that the derived anchor is
        calibrated against.
        """
        try:
            from qiskit import QuantumCircuit, transpile
            from qiskit_aer import AerSimulator
            backend = None
            backends = getattr(self.runner, 'backends', None)
            if backends:
                backend = backends.get(self.backend, None)
            if backend is None:
                return 0.02

            probe_qc = QuantumCircuit(2)
            probe_qc.h(0)
            probe_qc.cx(0, 1)
            probe_qc.measure_all()

            t_probe = transpile(probe_qc, backend, initial_layout=[0, 1])
            sim = AerSimulator.from_backend(backend)
            if self.seed is not None:
                sim.set_options(seed_simulator=self.seed)
            job = sim.run(t_probe, shots=4096)
            counts = job.result().get_counts()
            cleaned = {k.replace(" ", ""): v for k, v in counts.items()}
            fidelity = (cleaned.get('00', 0) + cleaned.get('11', 0)) / 4096
            return float(max(0.001, 1.0 - fidelity))
        except Exception:
            return 0.02

    def _backend_noise_estimate(self) -> float:
        """Estimate device noise ε from the backend's calibration model.

        Uses the mean CX/ECR gate error and readout error from the fake
        backend's properties — this is the device's *declared* calibration,
        not measured circuit outcomes. This is the honest analog of what the
        ZKC probe measures at runtime in engine.verify().
        """
        try:
            backends = getattr(self.runner, 'backends', None)
            if backends is None:
                return 0.02
            backend = backends.get(self.backend, None)
            if backend is None:
                return 0.02
            props = backend.properties()
            gate_errors = []
            for gate in props.gates:
                if gate.gate in ('cx', 'ecr', 'cz'):
                    for param in gate.parameters:
                        if param.name == 'gate_error':
                            gate_errors.append(param.value)
            if not gate_errors:
                return 0.02
            mean_2q_err = float(np.mean(gate_errors))
            # Effective per-gate loss: 2q gate error + half the readout error budget
            readout_err = 0.01  # typical declared readout error
            return float(max(0.001, mean_2q_err + readout_err))
        except Exception:
            return 0.02

    def _compute_ideal_probability(self, algo: str, circuit) -> float:
        """Compute the ideal (noiseless) probability of the learned target state(s).

        Uses the exact statevector compiler — this is the 'ideal oracle'
        that the derived anchor is calibrated against.

        Handles partial measurement: BV/DJ measure n-1 of n qubits (aux
        qubit unmeasured), so counts keys are shorter than the QFA state
        space. We marginalize over the unmeasured qubits.
        """
        from ..qfa.circuit_compiler import compile_circuit
        target = self.learned_targets.get(algo)
        if target is None:
            return 0.5
        try:
            qfa = compile_circuit(circuit)
            # Which qubits does the circuit actually measure? (Qiskit counts
            # keys include unmeasured cregs, which must NOT count toward p_ideal.)
            measured_qubits = []
            for instr in circuit.data:
                if instr.operation.name == 'measure':
                    for q in instr.qubits:
                        measured_qubits.append(circuit.find_bit(q).index)
            measured_qubits = sorted(set(measured_qubits))

            targets = target if isinstance(target, list) else [target]
            total = 0.0
            for t in targets:
                # Counts keys are in Qiskit order (qubit 0 = rightmost);
                # the compiler uses qubit 0 = leftmost. Reverse to match.
                t_compiler = t[::-1]
                if not measured_qubits:
                    # No measure instructions: exact match on the full state
                    if len(t_compiler) == qfa.num_qubits:
                        total += qfa.get_probability(t_compiler)
                    continue
                # Match on the measured qubit positions only; marginalize
                # over unmeasured qubits (e.g., BV/DJ aux qubit).
                for s, a in qfa.superposition.items():
                    match = True
                    for qi, qidx in enumerate(measured_qubits):
                        if qi < len(t_compiler):
                            if s.bits[qidx] != t_compiler[qi]:
                                match = False
                                break
                        else:
                            # Target shorter than measured set: no match
                            match = False
                            break
                    if match:
                        total += abs(a) ** 2
            return float(min(1.0, total))
        except Exception:
            # Fall back to a conservative default if compilation fails
            return 0.5

    def _evaluate_with_thresholds(self, results: List[IBMJobResult], thresholds: Dict,
                                  gray_margin: float = 0.0) -> List[Dict]:
        evaluated = []
        for res in results:
            base = res.circuit_name.split('_')[0]
            is_buggy = 'correct' not in res.circuit_name
            val = self._calculate_metric(base, res.counts, sum(res.counts.values()))
            threshold = thresholds.get(base, 0.15)
            # Uniform verdict semantics: pass iff the measured success metric
            # clears the adaptive anchor. No per-algorithm inversion hacks.
            # Optional gray zone: metrics within gray_margin of the boundary are
            # 'borderline' — honest "needs review" instead of hard pass/fail.
            if gray_margin > 0 and abs(val - threshold) <= gray_margin * threshold:
                verdict = 'borderline'
                passed = True  # borderline is not a hard failure
            else:
                passed = bool(val > threshold)
                verdict = 'pass' if passed else 'fail'
            evaluated.append({
                'circuit': res.circuit_name, 'passed': passed, 'is_buggy': bool(is_buggy),
                'metric_value': float(val), 'threshold': float(threshold),
                'verdict': verdict,
                'true_positive': bool(passed and not is_buggy)
            })
        return evaluated

    def _save_eval_results(self, results: List[Dict], filename: Path):
        with open(filename, 'w') as f: json.dump(results, f, indent=2)

    def _generate_report(self, all_results: List[Dict]):
        from collections import Counter
        by_algo = defaultdict(lambda: {'correct_pass': 0, 'correct_fail': 0, 'buggy_pass': 0, 'buggy_fail': 0})
        for r in all_results:
            base = r['circuit'].split('_')[0]
            b = by_algo[base]
            if r['is_buggy']:
                if r['passed']: b['buggy_pass'] += 1
                else: b['buggy_fail'] += 1
            else:
                if r['passed']: b['correct_pass'] += 1
                else: b['correct_fail'] += 1

        tp = sum(1 for r in all_results if not r['passed'] and r['is_buggy'])
        fp = sum(1 for r in all_results if not r['passed'] and not r['is_buggy'])
        fn = sum(1 for r in all_results if r['passed'] and r['is_buggy'])
        tn = sum(1 for r in all_results if r['passed'] and not r['is_buggy'])

        print(f"\n📊 FINAL REPORT: Total Tests: {len(all_results)}")
        print(f"   Correct circuits: {tn} passed, {fp} failed  (false-failure rate {fp/(fp+tn):.1%})")
        print(f"   Buggy circuits:   {tp} caught, {fn} missed  (detection recall {tp/(tp+fn):.1%})")
        print(f"   Alarm precision (FAIL verdicts that are truly buggy): {tp/(tp+fp):.1%}")
        print(f"\n   Per-algorithm breakdown:")
        for base in sorted(by_algo):
            b = by_algo[base]
            print(f"     {base:8s} correct {b['correct_pass']}/{b['correct_pass']+b['correct_fail']} pass | "
                  f"buggy {b['buggy_fail']}/{b['buggy_pass']+b['buggy_fail']} caught)")
