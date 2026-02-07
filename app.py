
import streamlit as st
import pandas as pd
import plotly.express as px
import re
import PyPDF2
from io import BytesIO

st.set_page_config(page_title="AARIVA: Master Fusion", layout="wide", page_icon="🧬")

# --- CSS BRANDING ---
st.markdown("""
    <style>
    .header {font-size: 2.5rem; color: #004aad; font-weight: 700;}
    </style>
""", unsafe_allow_html=True)

# --- 1. THE "0h 17m" TIME PARSER ---
def parse_duration(val):
    # Converts "0h 17m" or "0h 11m" to numeric minutes
    if pd.isna(val): return 0
    val = str(val).lower().strip()
    
    hours = 0
    minutes = 0
    
    try:
        # Extract Hours
        if 'h' in val:
            parts = val.split('h')
            hours = int(parts[0].strip())
            rest = parts[1]
        else:
            rest = val
            
        # Extract Minutes
        if 'm' in rest:
            minutes = int(rest.split('m')[0].strip())
        elif rest.strip().isdigit():
            minutes = int(rest.strip())
            
        return (hours * 60) + minutes
    except:
        return 0

# --- 2. THE PDF SCORE EXTRACTOR ---
def parse_pdf_scores(pdf_file):
    # Extracts "StudentID: 2025mi01" and "My Score (13/30)" from ExamSoft PDF
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    
    # Regex Patterns based on your file snippet
    # Find all IDs
    ids = re.findall(r'StudentID:\s*(\w+)', text)
    
    # Find all Scores (Pattern: "My Score (13/30)")
    # We look for digits before "/30"
    scores = re.findall(r'My Score\s*\(\s*(\d+(\.\d+)?)', text)
    
    # Align them (Assuming order is preserved in PDF report)
    data = []
    min_len = min(len(ids), len(scores))
    
    for i in range(min_len):
        # Clean ID
        sid = ids[i].strip().lower()
        # Extract score (taking the first group of the regex match)
        scr = float(scores[i][0]) 
        # Normalize to % (Assuming out of 30)
        pct = (scr / 30) * 100
        data.append({'Clean_ID': sid, 'Score': pct, 'Raw_Score': scr})
        
    return pd.DataFrame(data)

# --- 3. DATA LOADER ---
def load_data(file_time, file_pdf):
    # A. LOAD TIME (CSV)
    try:
        df_time = pd.read_csv(file_time)
        
        # Identify Columns
        id_col = next(c for c in df_time.columns if 'student' in c.lower() and 'id' in c.lower())
        time_col = next(c for c in df_time.columns if 'total' in c.lower() or 'active' in c.lower())
        
        # Clean & Parse
        df_time['Clean_ID'] = df_time[id_col].astype(str).str.strip().str.lower()
        df_time['Minutes'] = df_time[time_col].apply(parse_duration)
        
    except Exception as e:
        st.error(f"❌ Error reading Time CSV: {e}")
        return None

    # B. LOAD SCORES (PDF)
    try:
        df_score = parse_pdf_scores(file_pdf)
        if df_score.empty:
            st.error("❌ Could not extract scores from PDF. Ensure format matches 'My Score (X/30)'.")
            return None
    except Exception as e:
        st.error(f"❌ Error reading PDF: {e}")
        return None

    # C. MERGE
    merged = pd.merge(df_score, df_time, on='Clean_ID', how='inner')
    
    # D. DIAGNOSE (P-LENS)
    def diagnose(row):
        t = row['Minutes']
        s = row['Score'] # Percentage
        
        if t < 20 and s < 60: return "Rapid Guesser (Disengaged)"
        if t > 50 and s < 60: return "Struggling Learner"
        if t < 20 and s > 80: return "Mastery (High Velocity)"
        return "Stable"

    merged['Profile'] = merged.apply(diagnose, axis=1)
    return merged

# --- UI ---
def main():
    st.markdown("<div class='header'>AARIVA: Logic Fusion</div>", unsafe_allow_html=True)
    st.info("Upload your specific ExamSoft files to run the P-LENS Diagnosis.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 1. Velocity (Time)")
        f_time = st.file_uploader("Upload 'Mid-ElapsedTime...csv'", type=['csv', 'xlsx'])
    with c2:
        st.markdown("### 2. Competency (PDF Report)")
        f_pdf = st.file_uploader("Upload 'Mid-MultipleETs...pdf'", type=['pdf'])

    if f_time and f_pdf:
        if st.button("🚀 Run Analysis"):
            with st.spinner("Cracking PDF & Parsing Time Logs..."):
                df = load_data(f_time, f_pdf)
                
                if df is not None:
                    st.success(f"✅ Successfully Analyzed {len(df)} Students!")
                    
                    # METRICS
                    rapid = df[df['Profile'].str.contains("Rapid")]
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Rapid Guessers", len(rapid), delta="Burnout Risk", delta_color="inverse")
                    c2.metric("Avg Score", f"{int(df['Score'].mean())}%")
                    c3.metric("Avg Time", f"{int(df['Minutes'].mean())} min")
                    
                    # PLOT
                    fig = px.scatter(df, x="Minutes", y="Score", color="Profile", hover_data=["Clean_ID", "Raw_Score"],
                                     title="Velocity vs. Performance Matrix",
                                     color_discrete_map={"Rapid Guesser (Disengaged)": "red", "Stable": "blue"})
                    fig.add_vline(x=20, line_dash="dash", line_color="red")
                    fig.add_hline(y=60, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(df)

if __name__ == "__main__":
    main()
