from dataclasses import dataclass, field
from typing import Set, Dict, Tuple
import graphviz

@dataclass
class BuchiAutomaton:
    states: Set[str]
    alphabet: Set[str]
    transitions: Dict[Tuple[str, str], str] = field(default_factory=dict)
    initial_state: str = "q0"
    accepting_states: Set[str] = field(default_factory=set)
    violating_states: Set[str] = field(default_factory=set)
    operator: str = "F"
    
    def add_transition(self, from_state: str, guard: str, to_state: str):
        self.transitions[(from_state, guard)] = to_state
    
    def visualize(self, filename: str = "spec_automaton"):
        dot = graphviz.Digraph()
        dot.attr(rankdir='LR')
        
        for state in self.states:
            shape = "doublecircle" if state in self.accepting_states else "circle"
            dot.node(state, shape=shape)
        
        for (src, guard), dst in self.transitions.items():
            label = guard if guard != "True" else "Σ"
            dot.edge(src, dst, label=label)
        
        dot.render(filename, format='png', cleanup=True)
        return f"{filename}.png"

class SpecQFABuilder:
    @staticmethod
    def from_ltl(ltl_spec: dict) -> BuchiAutomaton:
        op = ltl_spec['operator']
        pred = ltl_spec['predicate']
        
        if op == 'F':
            ba = SpecQFABuilder._build_eventually(pred)
            ba.operator = 'F'
            return ba
        elif op == 'G':
            ba = SpecQFABuilder._build_globally(pred)
            ba.operator = 'G'
            return ba
        elif op.startswith('F<='):
            k = int(op.split('<=')[1])
            ba = SpecQFABuilder._build_bounded_eventually(pred, k)
            ba.operator = f'F<={k}'
            return ba
        elif op.startswith('G<='):
            k = int(op.split('<=')[1])
            ba = SpecQFABuilder._build_bounded_globally(pred, k)
            ba.operator = f'G<={k}'
            return ba
        else:
            raise ValueError(f"Unsupported operator: {op}")
    
    @staticmethod
    def _build_eventually(pred: dict) -> BuchiAutomaton:
        ba = BuchiAutomaton(
            states={'q0', 'q1'},
            alphabet={'sat', 'unsat'},
            initial_state='q0',
            accepting_states={'q1'},
            operator='F'
        )
        ba.add_transition('q0', 'sat', 'q1')
        ba.add_transition('q0', 'unsat', 'q0')
        ba.add_transition('q1', 'sat', 'q1')
        ba.add_transition('q1', 'unsat', 'q1')
        ba.predicate = pred
        return ba
    
    @staticmethod
    def _build_globally(pred: dict) -> BuchiAutomaton:
        ba = BuchiAutomaton(
            states={'q0', 'q1'},
            alphabet={'sat', 'unsat'},
            initial_state='q0',
            accepting_states={'q0'},
            violating_states={'q1'},
            operator='G'
        )
        ba.add_transition('q0', 'sat', 'q0')
        ba.add_transition('q0', 'unsat', 'q1')
        ba.add_transition('q1', 'sat', 'q1')
        ba.add_transition('q1', 'unsat', 'q1')
        ba.predicate = pred
        return ba
    
    @staticmethod
    def _build_bounded_eventually(pred: dict, k: int) -> BuchiAutomaton:
        states = {f'q{i}' for i in range(k+1)} | {'q_sat', 'q_fail'}
        ba = BuchiAutomaton(
            states=states,
            alphabet={'sat', 'unsat'},
            initial_state='q0',
            accepting_states={'q_sat'},
            violating_states={'q_fail'},
            operator=f'F<={k}'
        )
        
        for i in range(k):
            ba.add_transition(f'q{i}', 'sat', 'q_sat')
            ba.add_transition(f'q{i}', 'unsat', f'q{i+1}')
        
        ba.add_transition(f'q{k}', 'sat', 'q_sat')
        ba.add_transition(f'q{k}', 'unsat', 'q_fail')
        ba.add_transition('q_sat', 'sat', 'q_sat')
        ba.add_transition('q_sat', 'unsat', 'q_sat')
        ba.add_transition('q_fail', 'sat', 'q_fail')
        ba.add_transition('q_fail', 'unsat', 'q_fail')
        
        ba.predicate = pred
        ba.bound = k
        return ba
    
    @staticmethod
    def _build_bounded_globally(pred: dict, k: int) -> BuchiAutomaton:
        states = {f'q{i}' for i in range(k+1)} | {'q_ok', 'q_violated'}
        ba = BuchiAutomaton(
            states=states,
            alphabet={'sat', 'unsat'},
            initial_state='q0',
            accepting_states={'q_ok'} | {f'q{i}' for i in range(k+1)},
            violating_states={'q_violated'},
            operator=f'G<={k}'
        )
        
        for i in range(k):
            ba.add_transition(f'q{i}', 'sat', f'q{i+1}')
            ba.add_transition(f'q{i}', 'unsat', 'q_violated')
        
        ba.add_transition(f'q{k}', 'sat', 'q_ok')
        ba.add_transition(f'q{k}', 'unsat', 'q_violated')
        ba.add_transition('q_violated', 'sat', 'q_violated')
        ba.add_transition('q_violated', 'unsat', 'q_violated')
        
        ba.predicate = pred
        ba.bound = k
        return ba
