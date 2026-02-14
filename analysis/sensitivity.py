"""
Sensitivity Analysis (The "ROC" Proof)
Simulates varying the Safety Margin to prove the robustness of the 100% Recall.
"""
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path

def plot_sensitivity_sweep():
    # 1. Load the latest experiment data
    results_dir = Path("outputs/experiments")
    files = sorted(results_dir.glob("*.json"), key=lambda f: f.stat().st_mtime)
    if not files:
        print("❌ No data found! Run tests/test_week3.py first.")
        return
    
    latest_file = files[-1]
    print(f"📊 Analyzing: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)

    # 2. Define the Sweep
    # We will multiply the threshold by a factor (e.g., 0.8x to 1.2x)
    # Factor < 1.0 = Looser (Easier to pass)
    # Factor > 1.0 = Stricter (Harder to pass)
    modifiers = np.linspace(0.80, 1.20, 50) 
    
    stats = []

    for mod in modifiers:
        tp, fp, fn, tn = 0, 0, 0, 0
        
        for entry in data:
            if 'metric_value' not in entry: continue
            
            algo = entry['circuit'].split('_')[0]
            val = entry['metric_value']
            # Apply the stress test modifier to the original threshold
            threshold = entry['threshold'] * mod
            
            is_buggy = entry['is_buggy']
            
            # Re-evaluate Pass/Fail logic
            if algo == 'qft':
                # QFT: Pass if val < threshold (Lower is better)
                # If we multiply threshold by 1.1, it gets LARGER (Looser)
                # If we multiply by 0.9, it gets SMALLER (Stricter)
                passed = val < threshold
            else:
                # Others: Pass if val > threshold (Higher is better)
                passed = val > threshold
            
            # Count metrics
            if passed and not is_buggy: tp += 1
            if not passed and is_buggy: tn += 1
            if passed and is_buggy:     fp += 1
            if not passed and not is_buggy: fn += 1

        # Calculate Recall & Precision for this specific modifier
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        
        stats.append({
            'Modifier': mod,
            'Recall': recall,
            'Precision': precision
        })

    df = pd.DataFrame(stats)

    # 3. Plot the Result
    plt.figure(figsize=(10, 6))
    sns.set_style("whitegrid")
    
    # Plot Recall (Blue Line)
    sns.lineplot(data=df, x='Modifier', y='Recall', label='Recall (Safety)', color='blue', linewidth=3)
    
    # Plot Precision (Red Line)
    sns.lineplot(data=df, x='Modifier', y='Precision', label='Precision (Accuracy)', color='red', linewidth=2, linestyle='--')
    
    # Add the "Sweet Spot" marker at 1.0 (Our actual algorithm)
    plt.axvline(x=1.0, color='green', linestyle=':', label='Current Adaptive Anchor')
    
    plt.title("Robustness Analysis: Sensitivity to Threshold Variations", fontsize=14)
    plt.xlabel("Threshold Multiplier (0.8 = Loose, 1.2 = Strict)", fontsize=12)
    plt.ylabel("Score (0.0 - 1.0)", fontsize=12)
    plt.ylim(0, 1.1)
    plt.legend()
    
    output_path = Path("outputs/plots/fig3_sensitivity.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path)
    print(f"✅ Saved Robustness Graph to: {output_path}")

if __name__ == "__main__":
    plot_sensitivity_sweep()
