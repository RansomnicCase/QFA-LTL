"""
Pluggable threshold strategies for Phase 1.

Each strategy computes a pass/fail threshold for a given algorithm class.
The verdict is uniform: pass iff metric_value > threshold (higher-is-better).

Strategies:
- AdaptiveZKC: volume-based anchor from ZKC probe (the proposed method)
- FixedThreshold: static 0.15 (naive baseline)
- HoeffdingBound: classical concentration inequality
- WilsonBound: Wilson score interval (statistical baseline)
- NoZKC: ablation — adaptive anchor with fixed ε=0.005 (no probe benefit)
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import numpy as np
from collections import defaultdict


class ThresholdStrategy(ABC):
    """Base class for threshold computation strategies."""

    name: str = "base"

    @abstractmethod
    def compute_threshold(self, algo: str, metric_values: List[float],
                          circuit=None, noise_estimate: Optional[float] = None) -> float:
        """Compute threshold for an algorithm class.

        Args:
            algo: algorithm name (e.g., 'ghz')
            metric_values: list of metric values from correct circuits in calibration set
            circuit: a representative circuit (for volume-based strategies)
            noise_estimate: ZKC probe loss ε (for probe-based strategies)
        Returns:
            float: the threshold
        """
        pass


class AdaptiveZKC(ThresholdStrategy):
    """Volume-based adaptive anchor from ZKC probe (proposed method)."""

    name = "adaptive_zkc"

    def __init__(self, floor: float = 0.10, scale: float = 0.98):
        self.floor = floor
        self.scale = scale

    def compute_threshold(self, algo, metric_values, circuit=None, noise_estimate=None):
        if circuit is None or noise_estimate is None:
            return 0.15  # fallback
        ops = circuit.count_ops()
        n_2q = sum(ops.get(g, 0) for g in ['cx', 'cz', 'ecr', 'ccx', 'cp'])
        width = circuit.num_qubits
        effective_volume = n_2q + (width * 0.1)
        error_rate = max(0.001, noise_estimate)
        anchor = ((1.0 - error_rate) ** effective_volume) * self.scale
        return max(self.floor, anchor)


class FixedThreshold(ThresholdStrategy):
    """Static threshold baseline."""

    name = "fixed"

    def __init__(self, threshold: float = 0.15):
        self.threshold = threshold

    def compute_threshold(self, algo, metric_values, circuit=None, noise_estimate=None):
        return self.threshold


class HoeffdingBound(ThresholdStrategy):
    """Hoeffding concentration inequality threshold.

    With probability >= 1-delta, the true mean is within epsilon of the sample mean.
    Threshold = mean - epsilon, where epsilon = sqrt(ln(1/delta) / (2n)).
    """

    name = "hoeffding"

    def __init__(self, delta: float = 0.05):
        self.delta = delta

    def compute_threshold(self, algo, metric_values, circuit=None, noise_estimate=None):
        if not metric_values:
            return 0.15
        n = len(metric_values)
        mean = np.mean(metric_values)
        epsilon = np.sqrt(np.log(1.0 / self.delta) / (2.0 * n))
        return max(0.05, mean - epsilon)


class WilsonBound(ThresholdStrategy):
    """Wilson score interval lower bound.

    Conservative binomial confidence bound on the success probability.
    """

    name = "wilson"

    def __init__(self, z: float = 1.96):
        self.z = z

    def compute_threshold(self, algo, metric_values, circuit=None, noise_estimate=None):
        if not metric_values:
            return 0.15
        n = len(metric_values)
        p_hat = np.mean(metric_values)
        z = self.z
        denom = 1 + z**2 / n
        center = (p_hat + z**2 / (2*n)) / denom
        margin = (z / denom) * np.sqrt(p_hat*(1-p_hat)/n + z**2/(4*n**2))
        return max(0.05, center - margin)


class NoZKC(ThresholdStrategy):
    """Ablation: adaptive anchor with fixed ε=0.005 (no probe benefit).

    Tests whether the ZKC probe itself adds value beyond blind volume scaling.
    """

    name = "no_zkc"

    def __init__(self, floor: float = 0.10, scale: float = 0.98, fixed_epsilon: float = 0.005):
        self.floor = floor
        self.scale = scale
        self.fixed_epsilon = fixed_epsilon

    def compute_threshold(self, algo, metric_values, circuit=None, noise_estimate=None):
        if circuit is None:
            return 0.15
        ops = circuit.count_ops()
        n_2q = sum(ops.get(g, 0) for g in ['cx', 'cz', 'ecr', 'ccx', 'cp'])
        width = circuit.num_qubits
        effective_volume = n_2q + (width * 0.1)
        error_rate = self.fixed_epsilon
        anchor = ((1.0 - error_rate) ** effective_volume) * self.scale
        return max(self.floor, anchor)


# Registry
STRATEGIES = {
    "adaptive_zkc": AdaptiveZKC,
    "fixed": FixedThreshold,
    "hoeffding": HoeffdingBound,
    "wilson": WilsonBound,
    "no_zkc": NoZKC,
}


def get_strategy(name: str, **kwargs) -> ThresholdStrategy:
    """Get a threshold strategy by name."""
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[name](**kwargs)
