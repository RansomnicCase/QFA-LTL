import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.qfa_verify.ltl.parser import parse_ltl
from src.qfa_verify.qfa.spec_automaton import SpecQFABuilder
from src.qfa_verify.monitoring.temporal_monitor import TemporalMonitor, BatchTemporalMonitor

def test_eventually():
    print("=== Testing F (Eventually) ===\n")
    spec = parse_ltl("F(prob(|11>) > 0.85)")
    print(f"Parsed: {spec}\n")
    
    qfa = SpecQFABuilder.from_ltl(spec)
    print(f"States: {qfa.states}")
    print(f"Initial: {qfa.initial_state}, Accepting: {qfa.accepting_states}\n")

    # Windowed semantics: predicate = fraction of |11> in the last 100 shots.
    # First 500 shots are |00> (frac 0.0), then 600 shots of |11>.
    # After 100 consecutive |11> shots the window fraction is 1.0 > 0.85 -> SAT.
    trace = ['00'] * 500 + ['11'] * 600
    monitor = TemporalMonitor(qfa, '11', 0.85, window_size=100)
    result, history = monitor.process_trace(trace)
    print(f"Windowed F(prob(|11>) > 0.85), 100-shot window: {'PASS' if result else 'FAIL'}")
    print(f"Steps to satisfy: {next((h.step for h in history if h.satisfaction.name == 'SAT'), 'Never')}")
    print(f"Final state: {history[-1].automaton_state}\n")

    # Single |11> in 1000 shots must NOT satisfy prob > 0.85.
    sparse = ['00'] * 999 + ['11']
    monitor2 = TemporalMonitor(qfa, '11', 0.85, window_size=100)
    res2, _ = monitor2.process_trace(sparse)
    print(f"Sparse trace (p=0.001): {'PASS (WRONG)' if res2 else 'FAIL (correct)'}\n")

def test_bounded_eventually():
    print("=== Testing F<=1000 (Bounded Eventually) ===")
    spec = parse_ltl("F<=1000(prob(|11>) > 0.85)")
    print(f"Parsed: {spec}\n")

    qfa = SpecQFABuilder.from_ltl(spec)
    print(f"States: {qfa.states}\n")

    # Never satisfies within the bound -> q_fail at step 1000.
    trace_fail = ['00'] * 1200 + ['11'] * 100
    monitor = TemporalMonitor(qfa, '11', 0.85, window_size=100)
    result, history = monitor.process_trace(trace_fail)
    print(f"Case (never sat within 1000 steps): {'PASS' if result else 'FAIL'}")
    print(f"Final state: {history[-1].automaton_state} (should be q_fail)\n")

def test_globally():
    print("=== Testing G (Globally) ===")
    spec = parse_ltl("G(prob(|00>) < 0.10)")
    qfa = SpecQFABuilder.from_ltl(spec)

    # Fraction of |00> stays < 0.10 in every 100-shot window -> G holds.
    # Evenly sprinkle |00> at 5% so no window exceeds the threshold.
    ok_trace = (['11'] * 19 + ['00']) * 50
    monitor = TemporalMonitor(qfa, '00', 0.10, comparison='<', window_size=100)
    result, history = monitor.process_trace(ok_trace)
    print(f"Trace with p(00)=0.05 spread evenly, G(prob(|00>) < 0.10): {'PASS' if result else 'FAIL'} (should PASS)")
    print(f"Final state: {history[-1].automaton_state}\n")

    # A burst of |00> pushes a window fraction above 0.10 -> violation.
    bad_trace = ['11'] * 800 + ['00'] * 300
    monitor2 = TemporalMonitor(qfa, '00', 0.10, comparison='<', window_size=100)
    result2, history2 = monitor2.process_trace(bad_trace)
    print(f"Burst trace, same spec: {'PASS (WRONG)' if result2 else 'FAIL (correct)'}")
    diag = monitor2.get_diagnostic()
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
