from src.qfa_verify.ltl.parser import parse_ltl
from src.qfa_verify.qfa.spec_automaton import SpecQFABuilder
from src.qfa_verify.monitoring.temporal_monitor import TemporalMonitor

def smoke_eventually():
    print('=== smoke_eventually ===')
    spec = parse_ltl("F(prob(|11>) > 0.85)")
    print('Parsed:', spec)
    qfa = SpecQFABuilder.from_ltl(spec)
    print('Operator:', getattr(qfa, 'operator', None))
    trace = ['00'] * 500 + ['11'] * 600
    monitor = TemporalMonitor(qfa, '11', 0.85)
    result, history = monitor.process_trace(trace)
    print('Result:', result)

if __name__ == '__main__':
    smoke_eventually()
