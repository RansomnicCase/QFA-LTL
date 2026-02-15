# verify.py
import argparse
import sys
from qiskit import QuantumCircuit
from src.qfa_verify.engine import UniversalVerifier

def main():
    parser = argparse.ArgumentParser(description="QFA-LTL Production Verifier")
    parser.add_argument("--circuit", required=True, help="Path to .qasm file")
    parser.add_argument("--spec", required=True, help="LTL Property (e.g. 'F(p > t)')")
    parser.add_argument("--metric", choices=['probability', 'parity', 'expectation'], 
                        default='probability', help="Success metric to use")
    parser.add_argument("--target", required=True, help="Target state(s). For parity, use '00,11'")
    parser.add_argument("--backend", default="fake_brisbane", help="Backend noise model")

    args = parser.parse_args()
    
    # Handle multi-target inputs for parity (e.g., GHZ)
    target = args.target.split(',') if ',' in args.target else args.target

    try:
        # 1. Initialize Engine
        engine = UniversalVerifier(backend_name=args.backend)
        
        # 2. Load Circuit
        qc = QuantumCircuit.from_qasm_file(args.circuit)
        
        # 3. Run Production Pipeline (includes ZKC)
        report = engine.verify(qc, args.spec, metric_type=args.metric, target_params=target)

        # 4. Formatted Output for Research Results
        print("\n" + "═"*50)
        print(f" 🛡️  QFA-LTL UNIVERSAL VERIFICATION REPORT")
        print("═"*50)
        print(f" CIRCUIT:      {args.circuit}")
        print(f" BACKEND:      {args.backend}")
        print(f" METRIC:       {args.metric.upper()}")
        print("-" * 50)
        
        # Hardware Health Section
        print(f" [ZKC] Probe Loss:     {report['calibration_loss']:.4f}")
        print(f" [ZKC] Adaptive Anchor: {report['threshold']:.4f}")
        print("-" * 50)
        
        # Logic Verdict Section
        print(f" [LOGIC] Measured Val: {report['metric_value']:.4f}")
        print(f" [VERDICT]:            {report['verdict'].upper()}")
        print("═"*50 + "\n")

    except Exception as e:
        import traceback
        print("\n[CRITICAL ERROR]")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
