import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

st.set_page_config(page_title="QFA-LTL Dashboard", layout="wide")
st.title("🛡️ QFA-LTL Framework Analysis")

exp_dir = "outputs/experiments"
files = [f for f in os.listdir(exp_dir) if f.endswith('.json')]
selected_file = st.sidebar.selectbox("Select Experiment Run", sorted(files, reverse=True))

def load_data(filename):
    with open(os.path.join(exp_dir, filename), 'r') as f:
        content = json.load(f)
    if isinstance(content, list): return {"results": content}
    return content

data = load_data(selected_file)
df = pd.DataFrame(data.get('results', []))

if not df.empty:
    # --- FIXED: Column Name Mapping ---
    # Agar column 'circuit' hai toh use 'algorithm' me rename kardo visualization ke liye
    if 'circuit' in df.columns:
        df = df.rename(columns={'circuit': 'algorithm'})
    if 'passed' in df.columns:
        df['verdict'] = df['passed'].apply(lambda x: 'pass' if x else 'fail')
    if 'is_buggy' in df.columns:
        df['type'] = df['is_buggy'].apply(lambda x: 'buggy' if x else 'correct')
    if 'metric_value' in df.columns:
        df['pass_rate'] = df['metric_value'] * 100

    # Top Metrics
    st.write(f"📊 **Total Circuits Tested:** {len(df)}")
    
    # Plotting (Ab 'algorithm' column hamesha exist karega)
    fig = px.bar(
        df, 
        x='algorithm', 
        y='pass_rate' if 'pass_rate' in df.columns else df.columns[0],
        color='type' if 'type' in df.columns else None,
        barmode='group',
        title="Verification Results (Normalized Columns)"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Raw Verification Data")
    st.dataframe(df, use_container_width=True)
else:
    st.error("Selected file is empty.")
