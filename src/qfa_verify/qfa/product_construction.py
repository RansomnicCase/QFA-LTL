"""
Product Construction: Circuit-QFA × Spec-QFA
Creates combined automaton for reachability analysis.
"""
from typing import Dict, Set, Tuple, List, Optional
from dataclasses import dataclass
from collections import deque
import numpy as np

from src.qfa_verify.qfa.circuit_compiler import CircuitQFA, BasisState
from src.qfa_verify.qfa.spec_automaton import BuchiAutomaton

@dataclass(frozen=True)
class ProductState:
    """State in product automaton: (circuit_basis, spec_state)"""
    basis: str  # e.g., "11"
    spec_state: str  # e.g., "q0"
    
    def __hash__(self):
        return hash((self.basis, self.spec_state))

@dataclass
class ProductTransition:
    """Transition in product automaton"""
    from_state: ProductState
    to_state: ProductState
    probability: float  # Transition probability
    observation: str  # 'sat' or 'unsat'

class ProductAutomaton:
    """
    Constructs product of Circuit-QFA and Spec-QFA.
    Used for static analysis to extract test thresholds.
    """
    
    def __init__(self, circuit_qfa: CircuitQFA, spec_qfa: BuchiAutomaton, 
                 target_basis: str, threshold: float):
        self.circuit = circuit_qfa
        self.spec = spec_qfa
        self.target = target_basis
        self.threshold = threshold
        
        # Product automaton components
        self.states: Set[ProductState] = set()
        self.transitions: List[ProductTransition] = []
        self.initial_state: Optional[ProductState] = None
        self.accepting_states: Set[ProductState] = set()
        
    def construct(self):
        """
        Build product automaton on-the-fly using BFS.
        States: (basis_state, spec_automaton_state)
        """
        # Initial state: circuit initial |0...0> + spec initial
        init_basis = '0' * self.circuit.num_qubits
        init_spec = self.spec.initial_state
        self.initial_state = ProductState(init_basis, init_spec)
        
        queue = deque([self.initial_state])
        visited = {self.initial_state}
        
        while queue:
            current = queue.popleft()
            self.states.add(current)
            
            # Check if this is accepting (spec in accepting state)
            if current.spec_state in self.spec.accepting_states:
                self.accepting_states.add(current)
            
            # Expand transitions
            # For each possible observation (measurement outcome)
            for basis_state in self.circuit.get_basis_states():
                basis_str = basis_state.bits
                prob = self.circuit.get_probability(basis_str)
                
                if prob < 1e-10:  # Skip negligible
                    continue
                
                # Check if this observation satisfies the predicate
                is_sat = self._check_satisfaction(basis_str, prob)
                obs = 'sat' if is_sat else 'unsat'
                
                # Get next spec state
                next_spec = self.spec.transitions.get(
                    (current.spec_state, obs), 
                    current.spec_state
                )
                
                next_prod = ProductState(basis_str, next_spec)
                
                # Record transition
                trans = ProductTransition(
                    from_state=current,
                    to_state=next_prod,
                    probability=prob,
                    observation=obs
                )
                self.transitions.append(trans)
                
                if next_prod not in visited:
                    visited.add(next_prod)
                    queue.append(next_prod)
    
    def _check_satisfaction(self, basis: str, prob: float) -> bool:
        """Check if basis state satisfies the LTL predicate"""
        # Simple case: basis matches target and prob > threshold
        if basis == self.target:
            return prob > self.threshold
        return False
    
    def find_min_accepting_probability(self) -> Tuple[float, List[ProductState]]:
        """
        Find minimum probability needed in target state to reach acceptance.
        Uses Dijkstra-like search on product graph.
        
        Returns:
            (min_probability, path)
        """
        if not self.accepting_states:
            return 0.0, []
        
        # BFS to find shortest path to accepting state
        # Weighted by negative log probability (to find max prob path)
        queue = [(0, self.initial_state, [self.initial_state])]
        visited = set()
        
        while queue:
            cost, current, path = queue.pop(0)
            
            if current in self.accepting_states:
                # Calculate actual probability of this path
                prob = self._calculate_path_probability(path)
                return prob, path
            
            if current in visited:
                continue
            visited.add(current)
            
            # Expand
            for trans in self.transitions:
                if trans.from_state == current:
                    new_path = path + [trans.to_state]
                    # Cost is negative log prob (for Dijkstra)
                    new_cost = cost - np.log(trans.probability + 1e-10)
                    queue.append((new_cost, trans.to_state, new_path))
                    queue.sort()  # Poor man's priority queue
        
        return 0.0, []
    
    def _calculate_path_probability(self, path: List[ProductState]) -> float:
        """Calculate probability of taking this path"""
        prob = 1.0
        for i in range(len(path)-1):
            # Find transition
            for trans in self.transitions:
                if trans.from_state == path[i] and trans.to_state == path[i+1]:
                    prob *= trans.probability
                    break
        return prob
    
    def analyze_reachability(self) -> Dict:
        """
        Full reachability analysis for threshold extraction.
        Returns diagnostic info.
        """
        if not self.states:
            self.construct()
        
        min_prob, path = self.find_min_accepting_probability()
        
        # Find critical state (where we transition to accepting)
        critical_step = None
        if path:
            for i, state in enumerate(path):
                if state in self.accepting_states:
                    critical_step = i
                    break
        
        return {
            'min_accepting_probability': min_prob,
            'path_length': len(path),
            'critical_step': critical_step,
            'num_product_states': len(self.states),
            'num_transitions': len(self.transitions),
            'is_reachable': len(self.accepting_states) > 0
        }
