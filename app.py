
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="AARIVA: ExamSoft Fusion", layout="wide", page_icon="🧬")

# --- CSS ---
st.markdown("""
    <style>
    .header {font-size: 2.5rem; color: #004aad; font-weight: 700;}
    .metric-card {background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #004aad;}
    </style>
""", unsafe_allow_html=True)

# --- 1. THE DATA CLEANER (Tailored for YOUR files) ---
def clean_id(val):
    # Standardize ID: " 2025MI01 " -> "2025mi01"
    return str(val).strip().lower()

def load_data(file_time, file_score, file_item):
    # --- A. PROCESS VELOCITY (Elapsed Time File) ---
    try:
        df_time = pd.read_excel(file_time)
        # Auto-detect ID and Time columns common in ExamSoft
        id_col_t = next((c for c in df_time.columns if 'id' in c.lower() or 'student' in c.lower()), None)
        time_col = next((c for c in df_time.columns if 'elapsed' in c.lower() or 'duration' in c.lower() or 'time' in c.lower()), None)
        
        if not time_col: 
            st.error("❌ Error: Could not find 'Elapsed Time' column in the first file.")
            return None
            
        # Clean Data
        df_time['Clean_ID'] = df_time[id_col_t].apply(clean_id)
        # Convert Excel time (sometimes fraction of day) to Minutes
        # If it's a number like 0.02 (excel day fraction), * 1440. If it's 35 (minutes), keep it.
        if df_time[time_col].mean() < 1: 
            df_time['Minutes'] = df_time[time_col] * 1440 
        else:
            df_time['Minutes'] = df_time[time_col]
            
        df_time = df_time[['Clean_ID', 'Minutes']]
    except Exception as e:
        st.error(f"Error reading Time File: {e}")
        return None

    # --- B. PROCESS COMPETENCY (MultipleETs/Score File) ---
    try:
        df_score = pd.read_excel(file_score) # or csv
        id_col_s = next((c for c in df_score.columns if 'id' in c.lower() or 'student' in c.lower()), None)
        score_col = next((c for c in df_score.columns if 'score' in c.lower() or 'mark' in c.lower() or 'percent' in c.lower()), None)
        
        if not score_col:
            st.error("❌ Error: Could not find 'Score' column in the second file.")
            return None
            
        df_score['Clean_ID'] = df_score[id_col_s].apply(clean_id)
        df_score.rename(columns={score_col: 'Score'}, inplace=True)
        df_score = df_score[['Clean_ID', 'Score']]
    except Exception as e:
        st.error(f"Error reading Score File: {e}")
        return None

    # --- C. MERGE THEM (The "Smoking Gun" Analysis) ---
    merged = pd.merge(df_score, df_time, on='Clean_ID', how='inner')
    
    # --- D. APPLY P-LENS LOGIC ---
    def diagnose(row):
        t = row['Minutes']
        s = row['Score']
        # THRESHOLDS (Adjustable)
        if t < 20 and s < 60: return "Rapid Guesser (High Risk)"
        if t > 50 and s < 60: return "Struggling Learner (Knowledge Gap)"
        if t < 20 and s > 85: return "Mastery (High Efficiency)"
        return "Stable / Consistent"

    merged['Profile'] = merged.apply(diagnose, axis=1)
    return merged

# --- 2. THE UI ---
def main():
    st.markdown("<div class='header'>AARIVA: ExamSoft Analyzer</div>", unsafe_allow_html=True)
    st.info("Upload your 3 ExamSoft Export files below to run the P-LENS Diagnosis.")

    c1, c2, c3 = st.columns(3)
    
    # UPLOADER 1: TIME
    with c1:
        st.markdown("**1. Velocity Data**")
        st.caption("Upload: `Mid-ElapsedTime...xlsx`")
        f_time = st.file_uploader("Drop Time File", type=['xlsx', 'csv'], key="t")

    # UPLOADER 2: SCORES
    with c2:
        st.markdown("**2. Competency Data**")
        st.caption("Upload: `Mid-MultipleETs...`")
        f_score = st.file_uploader("Drop Score File", type=['xlsx', 'csv'], key="s")

    # UPLOADER 3: ITEM ANALYSIS (Future Use)
    with c3:
        st.markdown("**3. Item Difficulty**")
        st.caption("Upload: `Item-Analysis...`")
        f_item = st.file_uploader("Drop Analysis File", type=['pdf', 'xlsx'], key="i")

    # --- RUN LOGIC ---
    if f_time and f_score:
        if st.button("🚀 Run AARIVA Fusion Engine"):
            with st.spinner("Triangulating Data Sources..."):
                df = load_data(f_time, f_score, f_item)
                
                if df is not None:
                    # --- RESULTS DASHBOARD ---
                    st.success(f"✅ Analysis Complete! Merged {len(df)} Student Records.")
                    
                    # 1. Metrics
                    rapid = len(df[df['Profile'].str.contains("Rapid")])
                    struggle = len(df[df['Profile'].str.contains("Struggling")])
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Rapid Guessers (Burnout Risk)", rapid, delta="Urgent")
                    m2.metric("Struggling Learners", struggle, delta="Needs Support")
                    m3.metric("Avg Cohort Velocity", f"{int(df['Minutes'].mean())} min")
                    
                    # 2. The P-LENS Graph (Smoking Gun)
                    fig = px.scatter(df, x="Minutes", y="Score", color="Profile", hover_data=["Clean_ID"],
                                     title="The P-LENS Matrix: Velocity vs. Outcome",
                                     color_discrete_map={
                                         "Rapid Guesser (High Risk)": "red",
                                         "Struggling Learner (Knowledge Gap)": "orange",
                                         "Stable / Consistent": "blue",
                                         "Mastery (High Efficiency)": "green"
                                     })
                    # Add Thesis Threshold Lines
                    fig.add_vline(x=20, line_dash="dash", line_color="red", annotation_text="Rapid Guess Limit")
                    fig.add_hline(y=60, line_dash="dash", line_color="grey", annotation_text="Pass Mark")
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 3. Data Table
                    with st.expander("📄 View Detailed Student Report"):
                        st.dataframe(df)

if __name__ == "__main__":
    main()
