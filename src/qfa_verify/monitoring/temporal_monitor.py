from typing import List, Dict, Tuple
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
    def __init__(self, spec_qfa, target_basis: str, threshold: float):
        self.spec = spec_qfa
        self.target = target_basis
        self.threshold = threshold
        self.history: List[MonitorState] = []
        
    def process_trace(self, shots: List[str]) -> Tuple[bool, List[MonitorState]]:
        current_auto_state = self.spec.initial_state
        self.history = []
        
        for t, outcome in enumerate(shots):
            is_sat = self._check_predicate(outcome, t+1)
            obs = 'sat' if is_sat else 'unsat'
            
            next_state = self.spec.transitions.get(
                (current_auto_state, obs), 
                current_auto_state
            )
            
            if next_state in self.spec.accepting_states:
                status = Satisfaction.SAT
            elif next_state in ['q_fail', 'q_violated']:
                status = Satisfaction.VIOLATED
            elif any(next_state == f'q{i}' for i in range(10000)):
                status = Satisfaction.PENDING
            else:
                status = Satisfaction.UNSAT
            
            prob = shots[:t+1].count(self.target) / (t+1) if t > 0 else 0
            
            state = MonitorState(
                step=t,
                automaton_state=next_state,
                satisfaction=status,
                probability=prob
            )
            self.history.append(state)
            current_auto_state = next_state
            
            if status == Satisfaction.VIOLATED:
                return False, self.history
            if status == Satisfaction.SAT and not self._is_globally_op():
                return True, self.history
        
        final_accept = current_auto_state in self.spec.accepting_states
        return final_accept, self.history
    
    def _check_predicate(self, outcome: str, step: int) -> bool:
        return outcome == self.target
    
    def _is_globally_op(self) -> bool:
        return any(s in ['q_violated', 'q_ok'] for s in self.spec.states)
    
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
            count = hist.get(self.target, 0)
            prob = count / total if total > 0 else 0
            
            is_sat = prob > self.threshold
            obs = 'sat' if is_sat else 'unsat'
            
            next_state = self.spec.transitions.get(
                (current_auto_state, obs),
                current_auto_state
            )
            
            if next_state in self.spec.accepting_states:
                status = Satisfaction.SAT
            elif next_state in ['q_fail', 'q_violated']:
                status = Satisfaction.VIOLATED
            else:
                status = Satisfaction.PENDING
            
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
        
        return current_auto_state in self.spec.accepting_states, self.history
