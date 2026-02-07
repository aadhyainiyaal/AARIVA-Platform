
import streamlit as st
import pandas as pd
import plotly.express as px
import re
import PyPDF2
from io import BytesIO

st.set_page_config(page_title="AARIVA: Master Fusion", layout="wide", page_icon="🧬")

# --- CSS ---
st.markdown("""
    <style>
    .header {font-size: 2.5rem; color: #004aad; font-weight: 700;}
    </style>
""", unsafe_allow_html=True)

# --- 1. TIME PARSER (0h 17m -> 17) ---
def parse_duration(val):
    if pd.isna(val): return 0
    val = str(val).lower().strip()
    try:
        hours = 0
        minutes = 0
        if 'h' in val:
            parts = val.split('h')
            hours = int(parts[0].strip())
            rest = parts[1]
        else:
            rest = val
        if 'm' in rest:
            minutes = int(rest.split('m')[0].strip())
        elif rest.strip().replace('.','',1).isdigit():
            minutes = float(rest.strip())
        return (hours * 60) + minutes
    except:
        return 0

# --- 2. PDF PARSER ---
def parse_pdf_scores(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    
    # Regex to find ID (e.g., 2025mi01)
    # Looking for 'StudentID' followed by alphanumerics
    ids = re.findall(r'StudentID:?\s*(\w+)', text, re.IGNORECASE)
    
    # Regex to find Score (e.g., My Score (13/30))
    # Looking for 'My Score' followed by (number/number)
    scores = re.findall(r'My Score\s*\((\d+(\.\d+)?)/', text, re.IGNORECASE)
    
    data = []
    # Safety: Match lengths
    min_len = min(len(ids), len(scores))
    
    for i in range(min_len):
        sid = ids[i].strip().lower()
        raw_score = float(scores[i][0])
        # Convert to percentage (Assuming /30 based on snippet)
        pct = (raw_score / 30) * 100
        data.append({'Clean_ID': sid, 'Score': pct})
        
    return pd.DataFrame(data)

# --- 3. ROBUST FILE LOADER (THE FIX) ---
def load_data(file_time, file_pdf):
    # A. LOAD TIME (Handle Encoding Errors)
    try:
        # Try default UTF-8 first
        df_time = pd.read_csv(file_time)
    except UnicodeDecodeError:
        try:
            # Try Latin-1 (Common for Excel CSVs)
            file_time.seek(0)
            df_time = pd.read_csv(file_time, encoding='latin1')
        except:
            st.error("❌ Critical Error: File encoding not supported. Please save CSV as UTF-8.")
            return None

    try:
        # Identify Columns dynamically
        cols = [c.lower() for c in df_time.columns]
        
        # Find ID Column
        id_col_name = next((c for c in df_time.columns if 'student' in c.lower() and 'id' in c.lower()), None)
        if not id_col_name:
             # Fallback: look for 2025mi patterns in first row
             pass 
             
        # Find Time Column (Total Time / Active Time)
        time_col_name = next((c for c in df_time.columns if 'total' in c.lower() or 'active' in c.lower()), None)
        
        if not id_col_name or not time_col_name:
            st.error(f"❌ Column Error. Found: {list(df_time.columns)}. Need 'StudentID' and 'Total Time'.")
            return None

        # Clean & Parse
        df_time['Clean_ID'] = df_time[id_col_name].astype(str).str.strip().str.lower()
        df_time['Minutes'] = df_time[time_col_name].apply(parse_duration)
        
    except Exception as e:
        st.error(f"❌ Logic Error processing CSV: {e}")
        return None

    # B. LOAD PDF
    try:
        df_score = parse_pdf_scores(file_pdf)
        if df_score.empty:
            st.warning("⚠️ Warning: No scores found in PDF. Check format.")
            return None
    except Exception as e:
        st.error(f"❌ PDF Error: {e}")
        return None

    # C. MERGE
    merged = pd.merge(df_score, df_time, on='Clean_ID', how='inner')
    
    # D. DIAGNOSE
    def diagnose(row):
        t = row['Minutes']
        s = row['Score']
        
        # LOGIC FROM THESIS
        if t < 20 and s < 60: return "Rapid Guesser (Disengaged)"
        if t > 50 and s < 60: return "Struggling Learner"
        if t < 20 and s > 80: return "Mastery"
        return "Stable"

    merged['Profile'] = merged.apply(diagnose, axis=1)
    return merged

# --- UI ---
def main():
    st.markdown("<div class='header'>AARIVA: Master Fusion</div>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        f_time = st.file_uploader("1. Upload Time CSV", type=['csv'])
    with c2:
        f_pdf = st.file_uploader("2. Upload Score PDF", type=['pdf'])

    if f_time and f_pdf:
        if st.button("🚀 Run Analysis"):
            with st.spinner("Processing..."):
                df = load_data(f_time, f_pdf)
                
                if df is not None and not df.empty:
                    st.success(f"✅ Merged {len(df)} Records!")
                    
                    # Graph
                    fig = px.scatter(df, x="Minutes", y="Score", color="Profile", 
                                     title="Velocity vs Performance",
                                     color_discrete_map={"Rapid Guesser (Disengaged)": "red", "Stable": "blue"})
                    fig.add_vline(x=20, line_dash="dash", line_color="red")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(df)
                elif df is not None:
                     st.error("No matching IDs found between CSV and PDF. Check StudentIDs.")

if __name__ == "__main__":
    main()
