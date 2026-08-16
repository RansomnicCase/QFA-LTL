from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum

class Satisfaction(Enum):
    SAT = "satisfied"
    UNSAT = "unsatisfied"
    PENDING = "pending"
    VIOLATED = "violated"

@dataclass
class MonitorState:
    step: int
    automaton_state: str
    satisfaction: Satisfaction
    probability: float

class TemporalMonitor:
    """
    Online LTL monitor over quantum measurement traces.

    Semantics: each time step t is a window of measurement shots; the atomic
    predicate prob(|b1> + |b2> + ...) c t is evaluated as the empirical
    fraction of shots in the window that land in any target basis, compared
    with the operator `c` from the LTL spec. The spec automaton then consumes
    the sat/unsat observation. This makes F(p>t), G(p<t), bounded variants,
    and multi-basis (parity-style) predicates all well-defined.
    """

    def __init__(self, spec_qfa, target_basis: Union[str, List[str]], threshold: float,
                 comparison: str = '>', window_size: Optional[int] = None):
        self.spec = spec_qfa
        self.targets = [target_basis] if isinstance(target_basis, str) else list(target_basis)
        self.threshold = threshold
        self.comparison = comparison
        self.window_size = window_size
        self.history: List[MonitorState] = []

    # -- predicate evaluation -------------------------------------------
    def _compare(self, frac: float) -> bool:
        comp = self.comparison
        if comp == '>':   return frac > self.threshold
        if comp == '>=':  return frac >= self.threshold
        if comp == '<':   return frac < self.threshold
        if comp == '<=':  return frac <= self.threshold
        if comp == '==':  return abs(frac - self.threshold) < 1e-9
        return frac > self.threshold

    def _window_fraction(self, window: List[str]) -> float:
        if not window:
            return 0.0
        return sum(1 for o in window if o in self.targets) / len(window)

    # -- automaton bookkeeping ------------------------------------------
    def _is_F_op(self) -> bool:
        op = getattr(self.spec, 'operator', 'F')
        return op == 'F' or op.startswith('F<=')

    def _observe(self, next_state: str) -> Satisfaction:
        if next_state in self.spec.accepting_states:
            return Satisfaction.SAT
        if next_state in getattr(self.spec, 'violating_states', set()):
            return Satisfaction.VIOLATED
        return Satisfaction.PENDING

    # -- trace processing ------------------------------------------------
    def process_trace(self, shots: List[str]) -> Tuple[bool, List[MonitorState]]:
        current_auto_state = self.spec.initial_state
        self.history = []

        for t, outcome in enumerate(shots):
            lo = 0 if self.window_size is None else max(0, t + 1 - self.window_size)
            window = shots[lo:t + 1]
            frac = self._window_fraction(window)
            is_sat = self._compare(frac)
            obs = 'sat' if is_sat else 'unsat'

            next_state = self.spec.transitions.get(
                (current_auto_state, obs),
                current_auto_state
            )

            status = self._observe(next_state)

            state = MonitorState(
                step=t,
                automaton_state=next_state,
                satisfaction=status,
                probability=frac
            )
            self.history.append(state)
            current_auto_state = next_state

            if status == Satisfaction.VIOLATED:
                return False, self.history
            # F-family: satisfaction is permanent once observed.
            if status == Satisfaction.SAT and self._is_F_op():
                return True, self.history

        # G-family: the property must hold at *every* step; final acceptance
        # is decided by the automaton state at trace end.
        final_accept = current_auto_state in self.spec.accepting_states
        return final_accept, self.history

    def _check_predicate(self, outcome: str, step: int) -> bool:
        """Back-compat single-shot predicate (unwindowed)."""
        return outcome in self.targets

    def get_diagnostic(self) -> Dict:
        if not self.history:
            return {}

        last = self.history[-1]
        return {
            'total_steps': len(self.history),
            'final_automaton_state': last.automaton_state,
            'satisfaction': last.satisfaction.value,
            'max_probability': max((s.probability for s in self.history), default=0),
            'first_violation_step': next(
                (s.step for s in self.history if s.satisfaction == Satisfaction.VIOLATED),
                None
            )
        }


class BatchTemporalMonitor(TemporalMonitor):
    def process_histograms(self, histograms: List[Dict[str, int]], window_size: int = 100):
        current_auto_state = self.spec.initial_state
        self.history = []

        for t, hist in enumerate(histograms):
            total = sum(hist.values())
            count = sum(hist.get(tgt, 0) for tgt in self.targets)
            prob = count / total if total > 0 else 0

            is_sat = self._compare(prob)
            obs = 'sat' if is_sat else 'unsat'

            next_state = self.spec.transitions.get(
                (current_auto_state, obs),
                current_auto_state
            )

            status = self._observe(next_state)

            state = MonitorState(
                step=t * window_size,
                automaton_state=next_state,
                satisfaction=status,
                probability=prob
            )
            self.history.append(state)
            current_auto_state = next_state

            if status == Satisfaction.VIOLATED:
                return False, self.history
            if status == Satisfaction.SAT and self._is_F_op():
                return True, self.history

        return current_auto_state in self.spec.accepting_states, self.history
