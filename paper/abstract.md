# Abstract (IEEE QCE 2026, v2 — after WS-1)

**Verification of Noisy Quantum Executions: A Derived, Calibration-Free Adaptive Anchor with a Characterized Detectability Frontier**

Verifying a quantum circuit on noisy intermediate-scale quantum (NISQ) hardware raises a question that classical equivalence checking does not answer: *is this run's measured behavior acceptable against its temporal specification, given the device's current noise?* Static test thresholds fail on bad calibration days (false failures) and miss faults on good days. We present an oracle-synthesis framework that derives the pass/fail threshold from first principles:

$$\tau = p_{\mathrm{ideal}} \cdot (1-\varepsilon)^V - \mathrm{Wilson}_{95\%}(n_{\mathrm{shots}})$$

where $p_{\mathrm{ideal}}$ is the exact, noise-free probability of the target basis state(s) computed by a validated statevector compiler (max $|\Delta p| = 8.9\times10^{-16}$ over 896 randomized states), $\varepsilon$ is the loss measured by a Bell-state calibration probe on the circuit's mapped physical qubits, and $V$ is the two-qubit-gate volume. The threshold is **calibration-free by construction**: no outcome data from the circuits under test is used — only ideal semantics and a device probe.

We evaluate on a 24-circuit benchmark suite (six algorithms × correct + three injected faults) under Brisbane calibration noise. Over 10 seeds with a 60/40 hold-out split: **0.0% false-failure rate** (all correct circuits pass on every seed), **100% alarm precision** (every fail verdict is a genuine fault), and 67% bug-detection recall. The undetected faults are *provably measurement-invisible*: they preserve the target-basis probability distribution (phase errors in QFT, distribution-preserving GHZ entanglement mutations). A calibration-drift simulation shows the anchor tracking device noise where a fixed 0.15 threshold false-fails correct circuits (2 of 8 drift days recovered). A comparison against a state-of-the-art equivalence checker (QCEC, 17/18 ideal-circuit detection) documents the complementary roles: ideal-unitary correctness versus noisy-run acceptability.

We contribute (i) a derived, calibration-free adaptive anchor with a statistical guarantee structure, (ii) a validated exact compiler with a tracked truncation-error bound, (iii) an empirical characterization of the detectability frontier of measurement-based verification, and (iv) an open benchmark suite with a fault taxonomy.
