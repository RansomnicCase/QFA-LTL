# verify.py
import argparse
import sys
import os
import json
import importlib.util
from datetime import datetime
from qiskit import QuantumCircuit
from src.qfa_verify.engine import UniversalVerifier

def load_circuit(file_path):
    """Robust loader for .qasm and .py files."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Circuit file not found: {file_path}")
    
    _, ext = os.path.splitext(file_path)
    
    if ext == '.qasm':
        return QuantumCircuit.from_qasm_file(file_path)
    
    elif ext == '.py':
        # Dynamic import to extract a circuit object from a Python script
        spec = importlib.util.spec_from_file_location("dynamic_circuit", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Priority check for common variable names
        for attr in ['qc', 'circuit', 'qf']:
            if hasattr(module, attr):
                obj = getattr(module, attr)
                if isinstance(obj, QuantumCircuit):
                    return obj
        raise ValueError(f"No Qiskit QuantumCircuit found in {file_path}. Ensure your variable is named 'qc' or 'circuit'.")
    
    else:
        raise ValueError(f"Unsupported format '{ext}'. Use .qasm or .py")

def main():
    parser = argparse.ArgumentParser(description="QFA-LTL Production Verifier")
    parser.add_argument("--circuit", required=True, help="Path to .qasm or .py file")
    parser.add_argument("--spec", required=True, help="LTL Property (e.g. 'F(prob(|11>) > 0.85)')")
    parser.add_argument("--metric", choices=['probability', 'parity', 'expectation'], 
                        default='probability', help="Success metric to use")
    parser.add_argument("--target", help="Target state(s). For parity, use '00,11'. Defaults to the LTL spec predicate basis.")
    parser.add_argument("--backend", default="fake_brisbane", help="Backend noise model")
    parser.add_argument("--noise", type=float, default=0.0, help="Adversarial noise injection probability (0.0 to 1.0)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible runs")
    parser.add_argument("--output", help="Optional path to save JSON report")

    args = parser.parse_args()
    
    # Handle multi-target inputs for parity (e.g., GHZ)
    target = args.target.split(',') if args.target and ',' in args.target else args.target

    try:
        # 1. Initialize Engine
        engine = UniversalVerifier(backend_name=args.backend, seed=args.seed)
        
        # 2. Load Circuit (New Robust Loader)
        qc = load_circuit(args.circuit)
        
        # 3. Run Production Pipeline (includes ZKC and Noise Injection)
        report = engine.verify(
            qc, 
            args.spec, 
            metric_type=args.metric, 
            target_params=target, 
            adversarial_noise=args.noise
        )

        # 4. Formatted Output for Research Results
        print("\n" + "═"*55)
        print(f" 🛡️  QFA-LTL UNIVERSAL VERIFICATION REPORT")
        print("═"*55)
        print(f" CIRCUIT:      {args.circuit}")
        print(f" BACKEND:      {args.backend}")
        print(f" METRIC:       {args.metric.upper()}")
        if args.noise > 0:
            print(f" ADVERSARIAL:  {args.noise*100:.1f}% INJECTED NOISE")
        print("-" * 55)
        
        # Hardware Health Section (ZKC)
        print(f" [ZKC] Probe Loss:      {report['calibration_loss']:.4f}")
        print(f" [ZKC] Adaptive Anchor:  {report['threshold']:.4f}")
        print("-" * 55)
        
        # Logic Verdict Section
        print(f" [LOGIC] Measured Val:  {report['metric_value']:.4f}")
        print(f" [VERDICT]:             {report['verdict'].upper()}")
        print("═"*55 + "\n")

        # 5. Structured Logging (Save to JSON)
        if args.output or True:  # Defaulting to true for Phase 3 checklist compliance
            report_path = args.output if args.output else f"outputs/verification_report.json"
            # Ensure output directory exists
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            
            structured_data = {
                "timestamp": datetime.now().isoformat(),
                "input_file": args.circuit,
                "backend": args.backend,
                "spec": args.spec,
                "adversarial_noise": args.noise,
                "seed": args.seed,
                "results": {
                    "verdict": report['verdict'],
                    "metric_value": report['metric_value'],
                    "threshold": report['threshold'],
                    "calibration_loss": report['calibration_loss']
                }
            }
            with open(report_path, 'w') as f:
                json.dump(structured_data, f, indent=4)
            print(f"✅ Report saved to {report_path}")

    except Exception as e:
        print("\n" + "!"*55)
        print(f" CRITICAL ERROR: {str(e)}")
        print("!"*55)
        sys.exit(1)

if __name__ == "__main__":
    main()
