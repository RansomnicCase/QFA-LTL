# run_comparison_study.py
import numpy as np
import matplotlib.pyplot as plt
import os
from src.qfa_verify.engine import UniversalVerifier

def run_comparison():
    print("🧪 Starting Phase 4: Comparison Study (Adaptive vs. Fixed)")
    
    # 1. Setup
    engine = UniversalVerifier(backend_name="fake_brisbane")
    from examples.stress_7q import qc  # Using our complex 7-qubit circuit
    
    fixed_threshold = 0.15
    noise_scaling = np.linspace(1.0, 5.0, 10) # 1x noise to 5x noise
    
    results = {
        "noise_lv": [],
        "metric_vals": [],
        "adaptive_anchors": [],
        "fixed_pass": [],
        "adaptive_pass": []
    }

    # 2. Run the sweep
    for scale in noise_scaling:
        # We simulate noise by artificially scaling the calibration loss 
        # to see how the engine's math reacts to "bad days" on hardware
        report = engine.verify(qc, "G(p > t)", metric_type="expectation", target_params="0000000")
        
        # Simulate hardware degradation: 
        # Measured value drops, and calibration loss (noise) increases
        sim_val = report['metric_value'] / (scale * 0.4 + 0.6)
        sim_noise = report['calibration_loss'] * scale
        
        # Re-calculate anchor based on simulated noise
        sim_anchor = engine._calculate_adaptive_anchor(qc, sim_noise)
        
        results["noise_lv"].append(scale)
        results["metric_vals"].append(sim_val)
        results["adaptive_anchors"].append(sim_anchor)
        results["fixed_pass"].append(sim_val >= fixed_threshold)
        results["adaptive_pass"].append(sim_val >= sim_anchor)

    # 3. Visualization for the Paper
    plt.figure(figsize=(10, 6))
    plt.plot(results["noise_lv"], results["metric_vals"], 'b-o', label='Measured Fidelity (Signal)')
    plt.plot(results["noise_lv"], results["adaptive_anchors"], 'r--', label='Adaptive Anchor (Ours)')
    plt.axhline(y=fixed_threshold, color='green', linestyle=':', label='Fixed Threshold (Legacy)')
    
    # Highlight the "False Failure Zone"
    plt.fill_between(results["noise_lv"], results["adaptive_anchors"], fixed_threshold, 
                     where=(np.array(results["metric_vals"]) < fixed_threshold) & (np.array(results["metric_vals"]) >= results["adaptive_anchors"]),
                     color='orange', alpha=0.3, label='False Failure Zone (Fixed Method)')

    plt.title("Hardware Sensitivity Study: Phase 4 Validation")
    plt.xlabel("Simulated Noise Multiplier")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    os.makedirs("outputs/plots", exist_ok=True)
    plt.savefig("outputs/plots/comparison_study.png")
    print("✅ Plot saved to outputs/plots/comparison_study.png")

    # 4. Generate LaTeX Table
    print("\n% LaTeX Results Table")
    print("\\begin{tabular}{|c|c|c|c|c|}")
    print("\\hline Noise & Metric & Fixed (0.15) & Adaptive & Improvement \\\\ \\hline")
    for i in range(len(noise_scaling)):
        f_res = "PASS" if results["fixed_pass"][i] else "FAIL"
        a_res = "PASS" if results["adaptive_pass"][i] else "FAIL"
        status = "RECOVERED" if (a_res == "PASS" and f_res == "FAIL") else "STABLE"
        print(f"{noise_scaling[i]:.1f}x & {results['metric_vals'][i]:.3f} & {f_res} & {a_res} & {status} \\\\")
    print("\\hline \\end{tabular}\n")

if __name__ == "__main__":
    run_comparison()
