"""
Week 4: Visualization Engine
Generates publication-ready figures from QFA-LTL experiment logs.
"""
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path

class QFAVisualizer:
    def __init__(self):
        self.results_dir = Path("outputs/experiments")
        self.plots_dir = Path("outputs/plots")
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        
        # Set professional academic style
        sns.set_theme(style="whitegrid", context="paper")
        plt.rcParams.update({'font.size': 12, 'figure.dpi': 300, 'font.family': 'serif'})

    def load_latest_data(self):
        # Get the most recent JSON result
        files = sorted(self.results_dir.glob("*.json"), key=lambda f: f.stat().st_mtime)
        if not files:
            print("❌ No results found. Run tests/test_week3.py first!")
            return None
        
        latest_file = files[-1]
        print(f"📊 Loading: {latest_file.name}")
        with open(latest_file, 'r') as f:
            return json.load(f)

    def generate_plots(self):
        data = self.load_latest_data()
        if not data: return
        
        df = pd.DataFrame(data)
        # Clean up algorithm names for the plot
        df['Algorithm'] = df['circuit'].apply(lambda x: x.split('_')[0].upper())
        df['Type'] = df['is_buggy'].apply(lambda x: "Buggy" if x else "Correct")
        df['Result'] = df['passed'].apply(lambda x: "Pass" if x else "Fail")

        self._plot_confusion_matrix(df)
        self._plot_algorithm_breakdown(df)

    def _plot_confusion_matrix(self, df):
        """Figure 1: Proof of 100% Recall (Safety)"""
        plt.figure(figsize=(7, 5))
        
        # Create cross-tabulation
        matrix = pd.crosstab(df['Type'], df['Result'], rownames=['Actual'], colnames=['Predicted'])
        
        # Ensure 'Correct' is the first row and 'Pass/Fail' columns exist
        matrix = matrix.reindex(index=['Correct', 'Buggy'], columns=['Pass', 'Fail'], fill_value=0)
        
        sns.heatmap(matrix, annot=True, fmt='d', cmap='Blues', cbar=False, annot_kws={"size": 14})
        plt.title("QFA-LTL Classification Performance")
        
        path = self.plots_dir / "fig1_confusion_matrix.png"
        plt.savefig(path, bbox_inches='tight')
        print(f"✅ Saved Confusion Matrix to {path}")
        plt.close()

    def _plot_algorithm_breakdown(self, df):
        """Figure 2: Pass Rate per Algorithm"""
        plt.figure(figsize=(10, 6))
        
        # Calculate pass percentages
        pass_rates = df.groupby(['Algorithm', 'Type'])['passed'].mean().reset_index()
        pass_rates['passed'] *= 100
        
        ax = sns.barplot(data=pass_rates, x='Algorithm', y='passed', hue='Type', 
                         palette={'Correct': '#2ecc71', 'Buggy': '#e74c3c'})
        
        plt.axhline(y=100, color='gray', linestyle='--', alpha=0.5)
        plt.ylabel("Pass Rate (%)")
        plt.title("Detection Resilience across Algorithm Classes")
        plt.ylim(0, 115)
        
        # Add values on top of bars
        for p in ax.patches:
            if p.get_height() > 0:
                ax.annotate(f'{p.get_height():.0f}%', 
                            (p.get_x() + p.get_width() / 2., p.get_height()), 
                            ha='center', va='center', fontsize=10, color='black', xytext=(0, 7),
                            textcoords='offset points')

        path = self.plots_dir / "fig2_pass_rates.png"
        plt.savefig(path, bbox_inches='tight')
        print(f"✅ Saved Pass Rate Chart to {path}")
        plt.close()

if __name__ == "__main__":
    visualizer = QFAVisualizer()
    visualizer.generate_plots()
