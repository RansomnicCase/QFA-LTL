import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ltl.parser import parse_ltl
from src.qfa.spec_automaton import SpecQFABuilder
from src.monitoring.temporal_monitor import TemporalMonitor, BatchTemporalMonitor

def test_eventually():
    print("=== Testing F (Eventually) ===")
    spec = parse_ltl("F(prob(|11>) > 0.85)")
    print(f"Parsed: {spec}")
    
    qfa = SpecQFABuilder.from_ltl(spec)
    print(f"States: {qfa.states}")
    print(f"Initial: {qfa.initial_state}, Accepting: {qfa.accepting_states}")
    
    trace = ['00'] * 500 + ['11'] * 600
    monitor = TemporalMonitor(qfa, '11', 0.85)
    result, history = monitor.process_trace(trace)
    
    print(f"Result: {'PASS' if result else 'FAIL'}")
    print(f"Steps to satisfy: {next((h.step for h in history if h.satisfaction.name == 'SAT'), 'Never')}")
    print(f"Final state: {history[-1].automaton_state}\n")

def test_bounded_eventually():
    print("=== Testing F<=1000 (Bounded Eventually) ===")
    spec = parse_ltl("F<=1000(prob(|11>) > 0.85)")
    print(f"Parsed: {spec}")
    
    qfa = SpecQFABuilder.from_ltl(spec)
    print(f"States: {qfa.states}")
    
    trace_fail = ['00'] * 1200 + ['11'] * 100
    monitor = TemporalMonitor(qfa, '11', 0.85)
    result, history = monitor.process_trace(trace_fail)
    print(f"Case (satisfies at 1200, bound=1000): {'PASS' if result else 'FAIL'}")
    print(f"Final state: {history[-1].automaton_state} (should be q_fail)\n")

def test_globally():
    print("=== Testing G (Globally) ===")
    spec = parse_ltl("G(prob(|00>) < 0.10)")
    qfa = SpecQFABuilder.from_ltl(spec)
    
    trace = ['11'] * 800 + ['00'] * 300
    monitor = TemporalMonitor(qfa, '00', 0.10)
    result, history = monitor.process_trace(trace)
    
    print(f"Result: {'PASS' if result else 'FAIL'}")
    diag = monitor.get_diagnostic()
    print(f"First violation at step: {diag.get('first_violation_step')}\n")

def test_batch_monitor():
    print("=== Testing Batch Monitor ===")
    spec = parse_ltl("F<=5(prob(|11>) > 0.80)")
    qfa = SpecQFABuilder.from_ltl(spec)
    
    batches = [
        {'00': 90, '11': 10},
        {'00': 85, '11': 15},
        {'00': 80, '11': 20},
        {'00': 20, '11': 80},
        {'00': 10, '11': 90}
    ]
    
    monitor = BatchTemporalMonitor(qfa, '11', 0.80)
    result, history = monitor.process_histograms(batches, window_size=100)
    
    print(f"Result: {'PASS' if result else 'FAIL'}")
    print(f"Probabilities: {[round(h.probability,2) for h in history]}\n")

def test_visualization():
    print("=== Testing Visualization ===")
    spec = parse_ltl("F<=3(prob(|11>) > 0.8)")
    qfa = SpecQFABuilder.from_ltl(spec)
    filename = qfa.visualize("outputs/test_automaton")
    print(f"Saved automaton diagram to: {filename}\n")

if __name__ == "__main__":
    test_eventually()
    test_bounded_eventually()
    test_globally()
    test_batch_monitor()
    test_visualization()
    print("✅ Week 1 Complete!")
