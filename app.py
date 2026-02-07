
import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(page_title="AARIVA: ExamSoft Fusion", layout="wide", page_icon="🧬")

# --- CSS ---
st.markdown("""
    <style>
    .header {font-size: 2.5rem; color: #004aad; font-weight: 700;}
    </style>
""", unsafe_allow_html=True)

# --- 1. THE SMART PARSER (The Fix) ---
def parse_time(val):
    # Converts '10:44' (str) -> 10.73 (float minutes)
    # Converts 15 (int) -> 15.0 (float)
    if pd.isna(val): return 0
    val = str(val).strip()
    
    # CASE 1: MM:SS format (e.g., "10:44")
    if ':' in val:
        try:
            parts = val.split(':')
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes + (seconds / 60)
        except:
            return 0
            
    # CASE 2: Already a number (e.g., "45" or 45)
    try:
        return float(val)
    except:
        return 0

def clean_id(val):
    return str(val).strip().lower()

# --- 2. DATA LOADER ---
def load_data(file_time, file_score):
    # --- A. PROCESS VELOCITY (Elapsed Time) ---
    try:
        # Read file
        if file_time.name.endswith('.csv'):
            df_time = pd.read_csv(file_time)
        else:
            df_time = pd.read_excel(file_time)

        # Find Columns
        id_col_t = next((c for c in df_time.columns if 'id' in c.lower() or 'student' in c.lower()), None)
        # Look for "Elapsed" or "Time" or "Duration"
        time_col = next((c for c in df_time.columns if 'elapsed' in c.lower() or 'time' in c.lower()), None)
        
        if not time_col:
            st.error("❌ Error: Could not find 'Elapsed Time' column.")
            return None

        # Clean ID
        df_time['Clean_ID'] = df_time[id_col_t].apply(clean_id)
        
        # APPLY THE FIX: Use the smart parser on the time column
        df_time['Minutes'] = df_time[time_col].apply(parse_time)
        
        df_time = df_time[['Clean_ID', 'Minutes']]
        
    except Exception as e:
        st.error(f"Error reading Time File: {e}")
        return None

    # --- B. PROCESS COMPETENCY (Scores) ---
    try:
        if file_score.name.endswith('.csv'):
            df_score = pd.read_csv(file_score)
        else:
            df_score = pd.read_excel(file_score)

        id_col_s = next((c for c in df_score.columns if 'id' in c.lower() or 'student' in c.lower()), None)
        score_col = next((c for c in df_score.columns if 'score' in c.lower() or 'mark' in c.lower() or 'percent' in c.lower()), None)
        
        if not score_col:
            st.error("❌ Error: Could not find 'Score' column.")
            return None
            
        df_score['Clean_ID'] = df_score[id_col_s].apply(clean_id)
        df_score.rename(columns={score_col: 'Score'}, inplace=True)
        
        # Force Score to be numeric
        df_score['Score'] = pd.to_numeric(df_score['Score'], errors='coerce').fillna(0)
        
        df_score = df_score[['Clean_ID', 'Score']]
    except Exception as e:
        st.error(f"Error reading Score File: {e}")
        return None

    # --- C. MERGE & DIAGNOSE ---
    merged = pd.merge(df_score, df_time, on='Clean_ID', how='inner')
    
    def diagnose(row):
        t = row['Minutes']
        s = row['Score']
        # THRESHOLDS
        if t < 15 and s < 60: return "Rapid Guesser (Disengaged)"
        if t > 50 and s < 60: return "Struggling Learner"
        if t < 15 and s > 85: return "Mastery (High Velocity)"
        return "Stable"

    merged['Profile'] = merged.apply(diagnose, axis=1)
    return merged

# --- 3. UI ---
def main():
    st.markdown("<div class='header'>AARIVA: ExamSoft Analyzer</div>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.info("1. Upload Time File (xlsx/csv)")
        f_time = st.file_uploader("Mid-ElapsedTime...", type=['xlsx', 'csv'], key="t")
    with c2:
        st.info("2. Upload Score File (xlsx/csv)")
        f_score = st.file_uploader("Mid-MultipleETs...", type=['xlsx', 'csv'], key="s")

    if f_time and f_score:
        if st.button("🚀 Run Analysis"):
            with st.spinner("Parsing timestamps..."):
                df = load_data(f_time, f_score)
                
                if df is not None:
                    st.success(f"✅ Success! Analyzed {len(df)} students.")
                    
                    # Metrics
                    rapid = len(df[df['Profile'].str.contains("Rapid")])
                    st.metric("Rapid Guessers found", rapid, delta="Urgent")
                    
                    # Chart
                    fig = px.scatter(df, x="Minutes", y="Score", color="Profile", 
                                     title="Velocity Matrix",
                                     color_discrete_map={"Rapid Guesser (Disengaged)": "red", "Stable": "blue"})
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(df)

if __name__ == "__main__":
    main()
