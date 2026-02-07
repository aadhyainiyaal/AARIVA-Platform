
import streamlit as st
import pandas as pd
import plotly.express as px
import PyPDF2
import re
from io import BytesIO

st.set_page_config(page_title="AARIVA Platform", layout="wide", page_icon="🧠")

# --- STYLING ---
st.markdown("""
    <style>
    .header {font-size: 2.5rem; color: #2E86C1; font-weight: 800;}
    .risk-alert {background-color: #ffe6e6; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4d4d;}
    .safe-alert {background-color: #e6fffa; padding: 15px; border-radius: 10px; border-left: 5px solid #00cc99;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'role' not in st.session_state: st.session_state.role = None
if 'db' not in st.session_state: st.session_state.db = None

# --- MOCK USERS ---
USERS = {
    "prof": {"pass": "admin123", "role": "Faculty", "name": "Dr. Sivapriya"},
    "student": {"pass": "learn2025", "role": "Student", "name": "Student User"}
}

# ==============================================================================
# LOGIC ENGINE
# ==============================================================================

def parse_time_str(t_str):
    # Converts "0h 17m" to 17.0
    if pd.isna(t_str): return 0
    t_str = str(t_str).strip().lower()
    
    try:
        if 'h' in t_str or 'm' in t_str:
            h, m = 0, 0
            # Remove all non-alphanumeric except space
            clean = re.sub(r'[^0-9hm\s]', '', t_str)
            parts = clean.split(' ')
            for p in parts:
                if 'h' in p: 
                    h = int(p.replace('h',''))
                if 'm' in p: 
                    m = int(p.replace('m',''))
            return (h*60) + m
        return 0
    except:
        return 0

def process_data(pdf_file, time_file):
    # 1. PARSE PDF SCORES
    pdf_data = []
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        current_sid = None
        
        for page in reader.pages:
            text = page.extract_text()
            
            # --- FIX: Robust Regex for ID ---
            sid_search = re.search(r"StudentID:\s*(\S+)", text)
            if sid_search:
                current_sid = sid_search.group(1).strip()
            
            # --- FIX: Robust Regex for Score ---
            # Handles newlines and spaces in "My Score (13/30)"
            score_matches = re.findall(r"My Score\s*[\r\n]*\s*\(\s*(\d+)/30\s*\)", text)
            
            for score in score_matches:
                if current_sid:
                    # Prevent duplicates
                    if not any(d['StudentID'] == current_sid for d in pdf_data):
                        pdf_data.append({'StudentID': current_sid, 'Score': int(score)})
                        
        df_scores = pd.DataFrame(pdf_data)
        if df_scores.empty:
            st.error("Could not find scores in PDF. Checked pattern: 'My Score (X/30)'")
            return None
            
    except Exception as e:
        st.error(f"PDF Error: {e}")
        return None

    # 2. PARSE TIME LOGS
    try:
        if time_file.name.endswith('.csv'):
            df_time = pd.read_csv(time_file)
        else:
            df_time = pd.read_excel(time_file)
            
        # Find Columns
        time_col = next((c for c in df_time.columns if 'total' in c.lower() or 'elapsed' in c.lower()), None)
        id_col = next((c for c in df_time.columns if 'id' in c.lower() and 'student' in c.lower()), None)
        
        if not time_col or not id_col:
            st.error("Excel Error: Need 'Total Time' and 'StudentID' columns.")
            return None
            
        # Clean Data
        df_time['Total_Minutes'] = df_time[time_col].apply(parse_time_str)
        df_time['StudentID'] = df_time[id_col].astype(str).str.strip()
        
    except Exception as e:
        st.error(f"Time File Error: {e}")
        return None

    # 3. MERGE
    try:
        df_scores['Match_ID'] = df_scores['StudentID'].str.lower().str.strip()
        df_time['Match_ID'] = df_time['StudentID'].str.lower().str.strip()
        
        merged = pd.merge(df_scores, df_time, on='Match_ID', how='inner')
        
        # 4. DIAGNOSE
        median_t = merged['Total_Minutes'].median()
        if pd.isna(median_t): median_t = 30 # Fallback
        
        def categorize(row):
            t = row['Total_Minutes']
            s = row['Score']
            # Thesis Logic
            if t < 20 and s < 18: return "Rapid Guesser (High Risk)"
            if t > 50 and s < 18: return "Struggling Learner"
            if t < 20 and s > 25: return "Mastery / Efficient"
            return "Deep Learner / Average"

        merged['Category'] = merged.apply(categorize, axis=1)
        return merged
        
    except Exception as e:
        st.error(f"Merge Error: {e}")
        return None

# ==============================================================================
# UI VIEWS
# ==============================================================================

def login_screen():
    st.markdown("<div class='header'>AARIVA Platform</div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u in USERS and USERS[u]['pass'] == p:
                    st.session_state.authenticated = True
                    st.session_state.role = USERS[u]['role']
                    st.session_state.user_name = USERS[u]['name']
                    st.rerun()
                else:
                    st.error("Invalid Credentials")

def faculty_dashboard():
    st.title("👨‍🏫 Faculty Command Center")
    
    with st.expander("📂 Upload Assessment Data", expanded=True):
        c1, c2 = st.columns(2)
        f_pdf = c1.file_uploader("1. PDF Report", type=['pdf'])
        f_time = c2.file_uploader("2. Time Log", type=['xlsx', 'csv'])
        
        if f_pdf and f_time:
            if st.button("🚀 Run P-LENS Analysis"):
                with st.spinner("Processing..."):
                    df = process_data(f_pdf, f_time)
                    if df is not None:
                        st.session_state.db = df
                        st.success(f"Success! {len(df)} Students Analyzed.")

    if st.session_state.db is not None:
        df = st.session_state.db
        
        # Metrics
        rapid = len(df[df['Category'].str.contains("Rapid")])
        st.metric("Rapid Guessers (Risk)", rapid, delta="Needs Attention", delta_color="inverse")
        
        # Chart
        fig = px.scatter(df, x="Total_Minutes", y="Score", color="Category", 
                         title="Speed vs. Accuracy Matrix",
                         color_discrete_map={"Rapid Guesser (High Risk)": "red", "Deep Learner / Average": "blue"})
        fig.add_hline(y=18, line_dash="dash", line_color="gray") # Pass Mark (60% of 30)
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("View Student List"):
            st.dataframe(df[['StudentID_x', 'Score', 'Total_Minutes', 'Category']])

def student_dashboard():
    st.title("🎓 Student Portal")
    if st.session_state.db is None:
        st.info("No active assessment data available.")
        return
        
    st.write("Check your performance diagnosis:")
    my_id = st.text_input("Enter Student ID (e.g. 2025MI01)")
    
    if my_id:
        df = st.session_state.db
        row = df[df['StudentID_x'].str.lower() == my_id.strip().lower()]
        
        if not row.empty:
            cat = row.iloc[0]['Category']
            score = row.iloc[0]['Score']
            
            if "Rapid" in cat:
                st.markdown(f"<div class='risk-alert'><h3>⚠️ Rapid Guessing Detected</h3>"
                            f"<p>You scored <b>{score}/30</b>. Your time was very fast compared to peers.</p>"
                            f"<b>Advice:</b> Slow down and review questions twice.</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='safe-alert'><h3>✅ You are on Track</h3>"
                            f"<p>Your learning velocity is sustainable.</p></div>", unsafe_allow_html=True)
        else:
            st.error("ID not found.")

# --- ROUTER ---
if not st.session_state.authenticated:
    login_screen()
else:
    with st.sidebar:
        st.write(f"Logged in as: **{st.session_state.user_name}**")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
            
    if st.session_state.role == "Faculty": faculty_dashboard()
    elif st.session_state.role == "Student": student_dashboard()
