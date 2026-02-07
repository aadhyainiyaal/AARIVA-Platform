
import streamlit as st
import pandas as pd
import plotly.express as px
import PyPDF2
import re
from io import BytesIO

st.set_page_config(page_title="AARIVA: Stealth Assessment", layout="wide", page_icon="🧠")

# --- GLOBAL STYLING ---
st.markdown("""
    <style>
    .header {font-size: 2.5rem; color: #2E86C1; font-weight: 800;}
    .student-card {background-color: #f0f8ff; padding: 20px; border-radius: 10px; border: 1px solid #2E86C1;}
    .risk-alert {background-color: #ffe6e6; padding: 20px; border-radius: 10px; border: 1px solid #ff4d4d;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE (The "Live Memory") ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'role' not in st.session_state: st.session_state.role = None
if 'db' not in st.session_state: st.session_state.db = None # Stores the processed student data

# --- AUTHENTICATION (Simulated Database) ---
USERS = {
    "prof": {"pass": "admin123", "role": "Faculty", "name": "Dr. Sivapriya"},
    "student": {"pass": "learn2025", "role": "Student", "name": "Student User"}
}

# ==============================================================================
# LOGIC ENGINE (YOUR SCRIPT ADAPTED)
# ==============================================================================

def parse_time_str(t_str):
    # Parses "0h 31m" or "10:45" or "45"
    if pd.isna(t_str): return 0
    t_str = str(t_str).strip().lower()
    
    # Format: "0h 31m"
    if 'h' in t_str or 'm' in t_str:
        h, m = 0, 0
        parts = t_str.split(' ')
        for p in parts:
            if 'h' in p: h = int(re.sub(r'[^0-9]', '', p))
            if 'm' in p: m = int(re.sub(r'[^0-9]', '', p))
        return h*60 + m
    
    # Format: "10:45" (Excel Time) -> Assume simple minute conversion if needed
    # (For this specific logic, we stick to the user's "0h 31m" request)
    return 0

def process_data(pdf_file, time_file):
    # 1. PARSE PDF
    pdf_data = []
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        current_sid = None
        
        for page in reader.pages:
            text = page.extract_text()
            # Regex from user script
            sid_matches = re.findall(r"StudentID:\s*(\S+)", text)
            for sid in sid_matches:
                current_sid = sid.strip()
            
            # Score Regex
            score_matches = re.findall(r"My Score\s*[
]*\s*\(\s*(\d+)/30\s*\)", text)
            for score in score_matches:
                if current_sid:
                    # Avoid duplicates
                    if not any(d['StudentID'] == current_sid for d in pdf_data):
                        pdf_data.append({'StudentID': current_sid, 'Score': int(score)})
                        
        df_scores = pd.DataFrame(pdf_data)
    except Exception as e:
        st.error(f"PDF Parsing Error: {e}")
        return None

    # 2. PARSE TIME FILE
    try:
        if time_file.name.endswith('.csv'):
            df_time = pd.read_csv(time_file)
        else:
            df_time = pd.read_excel(time_file)
        
        # Locate Time Column (Robust Search)
        time_col = next((c for c in df_time.columns if 'total' in c.lower() or 'elapsed' in c.lower()), None)
        id_col = next((c for c in df_time.columns if 'id' in c.lower()), None)
        
        if not time_col or not id_col:
            st.error("Could not find 'Total Time' or 'StudentID' columns in Excel/CSV.")
            return None

        # Apply Parsing
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
        
        # 4. CATEGORIZE (P-LENS)
        median_time = merged['Total_Minutes'].median()
        median_score = merged['Score'].median()
        
        def categorize(row):
            if row['Total_Minutes'] < median_time and row['Score'] < median_score:
                return "Rapid Guesser (High Risk)"
            elif row['Total_Minutes'] >= median_time and row['Score'] < median_score:
                return "Struggling Learner"
            elif row['Total_Minutes'] < median_time and row['Score'] >= median_score:
                return "Mastery / Efficient"
            else:
                return "Deep Learner"

        merged['Category'] = merged.apply(categorize, axis=1)
        return merged
        
    except Exception as e:
        st.error(f"Merge Error: {e}")
        return None

# ==============================================================================
# UI COMPONENTS
# ==============================================================================

def login_screen():
    st.markdown("<div class='header'>AARIVA Platform</div>", unsafe_allow_html=True)
    st.info("Log in to access Stealth Assessment data.")
    
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
    st.write("Upload assessment files to update the student database.")
    
    with st.expander("📂 Upload New Assessment Data", expanded=True):
        c1, c2 = st.columns(2)
        f_pdf = c1.file_uploader("1. ExamSoft PDF (Scores)", type=['pdf'])
        f_time = c2.file_uploader("2. Time Log (Excel/CSV)", type=['xlsx', 'csv'])
        
        if f_pdf and f_time:
            if st.button("🚀 Process & Update Database"):
                with st.spinner("Analyzing..."):
                    df = process_data(f_pdf, f_time)
                    if df is not None:
                        st.session_state.db = df
                        st.success(f"Database Updated! {len(df)} students tracked.")

    # VISUALIZATION
    if st.session_state.db is not None:
        df = st.session_state.db
        
        st.markdown("### 📊 Cohort Analysis")
        
        # Scatter Plot
        fig = px.scatter(df, x="Total_Minutes", y="Score", color="Category", 
                         hover_data=["StudentID_x"], size_max=10,
                         color_discrete_map={"Rapid Guesser (High Risk)": "red", "Deep Learner": "green"})
        
        # Add Median Lines
        median_time = df['Total_Minutes'].median()
        median_score = df['Score'].median()
        fig.add_vline(x=median_time, line_dash="dash", line_color="gray", annotation_text="Median Time")
        fig.add_hline(y=median_score, line_dash="dash", line_color="gray", annotation_text="Median Score")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # At Risk Table
        st.subheader("🚨 At-Risk Students (Rapid Guessers)")
        rapid = df[df['Category'].str.contains("Rapid")]
        st.dataframe(rapid[['StudentID_x', 'Score', 'Total_Minutes', 'Category']])

def student_dashboard():
    st.title("🎓 Student Portal")
    
    if st.session_state.db is None:
        st.warning("No active assessment data found. Please ask your Faculty to upload results.")
        return

    # Student ID Lookup (Simulating secure login for specific ID)
    st.info("Enter your Student ID to retrieve your private Stealth Assessment report.")
    my_id = st.text_input("My Student ID (e.g., 2025MI01)")
    
    if my_id:
        # Search DB
        df = st.session_state.db
        # Flexible match (case insensitive)
        student_record = df[df['StudentID_x'].str.lower() == my_id.lower().strip()]
        
        if not student_record.empty:
            row = student_record.iloc[0]
            cat = row['Category']
            score = row['Score']
            time = row['Total_Minutes']
            
            st.markdown("---")
            if "Rapid" in cat:
                st.markdown(f"<div class='risk-alert'><h3>⚠️ Alert: Rapid Guessing Detected</h3>"
                            f"<p>You scored <b>{score}/30</b> in <b>{int(time)} minutes</b>.</p>"
                            f"<p><b>Diagnosis:</b> You answered faster than the class average but with lower accuracy. "
                            f"This suggests disengagement or rushing.</p>"
                            f"<p><b>Recommendation:</b> Please meet with Dr. Sivapriya for a strategy review.</p></div>", 
                            unsafe_allow_html=True)
            elif "Struggling" in cat:
                st.info("Status: High Effort, Low Outcome. We recommend booking a tutor session.")
            else:
                st.markdown(f"<div class='student-card'><h3>✅ Status: On Track</h3>"
                            f"<p>Your learning velocity is optimized. Keep up the good work!</p></div>", 
                            unsafe_allow_html=True)
                            
            # Personal Plot
            st.write("Your Position in the Class:")
            fig = px.scatter(df, x="Total_Minutes", y="Score", color="Category", 
                         color_discrete_map={"Rapid Guesser (High Risk)": "lightgray", 
                                             "Deep Learner": "lightgray", 
                                             "Struggling Learner": "lightgray", 
                                             "Mastery / Efficient": "lightgray"})
            # Highlight Student
            fig.add_trace(px.scatter(student_record, x="Total_Minutes", y="Score").data[0])
            fig.update_traces(marker=dict(color='red', size=15), selector=dict(type='scatter'))
            st.plotly_chart(fig)
            
        else:
            st.error("ID not found in the current assessment database.")

# --- MAIN ROUTER ---
if not st.session_state.authenticated:
    login_screen()
else:
    with st.sidebar:
        st.write(f"User: **{st.session_state.user_name}**")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
            
    if st.session_state.role == "Faculty":
        faculty_dashboard()
    elif st.session_state.role == "Student":
        student_dashboard()
