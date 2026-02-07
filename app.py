
import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE SETUP ---
st.set_page_config(page_title="AARIVA Pro", layout="wide", page_icon="🧠")

# --- CSS BRANDING ---
st.markdown("""
    <style>
    .header {font-size: 3rem; color: #004aad; text-align: center; font-weight: 700;}
    .sub-header {font-size: 1.2rem; color: #666; text-align: center;}
    .stApp {background-color: #fafafa;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'role' not in st.session_state: st.session_state.role = None
if 'cohort_data' not in st.session_state: st.session_state.cohort_data = None

# --- DATABASE (Hardcoded for Beta) ---
USERS = {
    "prof": {"pass": "admin123", "role": "Faculty", "name": "Dr. Sivapriya"},
    "dean": {"pass": "dean2025", "role": "Dean", "name": "Dean of Medicine"},
    "student": {"pass": "learn2025", "role": "Student", "name": "Scholar Aadhya"}
}

# --- LOGIC ENGINE ---
def process_files(score_file, time_file):
    # In a real scenario, we merge these. For now, we read the CSV directly.
    try:
        if time_file.name.endswith('.csv'):
            df = pd.read_csv(time_file)
        else:
            df = pd.read_excel(time_file)
        
        # BASIC STEALTH LOGIC
        # We assume the file has columns: 'Student ID', 'Time', 'Score'
        # If not, we create dummy columns for the demo to prevent crash
        if 'Time' not in df.columns: df['Time'] = 50 # Default
        if 'Score' not in df.columns: df['Score'] = 75 # Default

        def categorize(row):
            if row['Time'] < 20 and row['Score'] < 60: return "Rapid Guesser"
            if row['Time'] > 60 and row['Score'] < 60: return "Struggling Learner"
            return "Stable"

        df['Profile'] = df.apply(categorize, axis=1)
        return df
    except Exception as e:
        return None

# --- LOGIN SCREEN ---
def login():
    st.markdown("<div class='header'>AARIVA</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Adaptive Analytics for Real-time Intelligent Velocity Assessment</div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.form("Login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u in USERS and USERS[u]['pass'] == p:
                    st.session_state.authenticated = True
                    st.session_state.role = USERS[u]['role']
                    st.session_state.user = USERS[u]['name']
                    st.rerun()
                else:
                    st.error("Access Denied")
    
    st.info("💡 Try: 'prof' / 'admin123' OR 'dean' / 'dean2025'")

# --- ROLE: FACULTY ---
def faculty_view():
    st.title(f"👨‍🏫 Faculty Dashboard | {st.session_state.user}")
    
    # 1. DATA INGESTION (THE NEW PART)
    with st.expander("📂 Phase 1: Upload Data", expanded=True):
        st.write("Upload your ExamSoft Exports here.")
        up_file = st.file_uploader("Upload CSV/Excel (Must have columns: Student ID, Time, Score)", type=['csv','xlsx'])
        
        if up_file:
            df = process_files(None, up_file)
            if df is not None:
                st.session_state.cohort_data = df
                st.success("✅ Data Successfully Ingested!")
            else:
                st.error("Error reading file.")

    # 2. ANALYTICS
    if st.session_state.cohort_data is not None:
        df = st.session_state.cohort_data
        
        c1, c2, c3 = st.columns(3)
        rapid_count = len(df[df['Profile'] == "Rapid Guesser"])
        c1.metric("Rapid Guessers", rapid_count, "High Risk")
        c2.metric("Cohort Size", len(df))
        c3.metric("Avg Velocity", f"{int(df['Time'].mean())} min")
        
        st.subheader("Risk Matrix")
        # Interactive Chart
        fig = px.scatter(df, x="Time", y="Score", color="Profile", hover_data=["Student ID"], 
                         title="Velocity vs Performance", color_discrete_map={"Rapid Guesser":"red", "Stable":"blue"})
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df)

# --- ROLE: DEAN ---
def dean_view():
    st.title("🏛️ Dean's Oversight")
    st.markdown("### Institutional Health Monitor")
    
    # Hardcoded Trend for Demo
    data = {'Year': ['2021', '2022', '2023', '2024'], 'Burnout Rate': [15, 22, 18, 12]}
    fig = px.line(data, x='Year', y='Burnout Rate', title="Longitudinal Burnout Trends")
    st.plotly_chart(fig)
    st.info("AARIVA has reduced Rapid Guessing by 6% since implementation.")

# --- ROLE: STUDENT ---
def student_view():
    st.title("🧠 Student Portal")
    st.info("Welcome, Scholar. Here is your feedback.")
    st.warning("⚠️ Velocity Alert: You finished in 18 minutes. The class average was 45 minutes. Please slow down.")

# --- ROUTER ---
if not st.session_state.authenticated:
    login()
else:
    with st.sidebar:
        st.write(f"Logged in: **{st.session_state.user}**")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
            
    if st.session_state.role == 'Faculty': faculty_view()
    elif st.session_state.role == 'Dean': dean_view()
    elif st.session_state.role == 'Student': student_view()
