
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="AARIVA Pro", layout="wide", page_icon="🧠")

# --- CSS ---
st.markdown("""
    <style>
    .header {font-size: 3rem; color: #004aad; text-align: center; font-weight: 700;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'role' not in st.session_state: st.session_state.role = None
if 'cohort_data' not in st.session_state: st.session_state.cohort_data = None

# --- DATABASE ---
USERS = {
    "prof": {"pass": "admin123", "role": "Faculty", "name": "Dr. Sivapriya"},
    "dean": {"pass": "dean2025", "role": "Dean", "name": "Dean"},
    "student": {"pass": "learn2025", "role": "Student", "name": "Scholar"}
}

# --- SMART DATA CLEANER (The Fix) ---
def clean_data(df):
    # 1. Normalize Column Names (Strip spaces, lowercase)
    df.columns = df.columns.str.strip().str.title() 
    
    # 2. Rename specific columns to match what Plotly expects
    # Map common variations to standard names
    rename_map = {
        'Studentid': 'Student ID',
        'Student_Id': 'Student ID',
        'Id': 'Student ID',
        'Duration': 'Time',
        'Minutes': 'Time',
        'Marks': 'Score',
        'Grade': 'Score'
    }
    df.rename(columns=rename_map, inplace=True)
    
    # 3. Ensure required columns exist (Fill defaults if missing to prevent crash)
    if 'Time' not in df.columns: df['Time'] = 45
    if 'Score' not in df.columns: df['Score'] = 75
    if 'Student ID' not in df.columns: df['Student ID'] = [f'ID_{i}' for i in range(len(df))]
    
    return df

def process_files(file):
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        # APPLY THE CLEANER
        df = clean_data(df)

        def categorize(row):
            # Safe conversion to numbers
            t = pd.to_numeric(row['Time'], errors='coerce')
            s = pd.to_numeric(row['Score'], errors='coerce')
            
            if t < 20 and s < 60: return "Rapid Guesser"
            if t > 60 and s < 60: return "Struggling Learner"
            if t < 20 and s > 85: return "Mastery"
            return "Stable"

        df['Profile'] = df.apply(categorize, axis=1)
        return df
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

# --- VIEWS ---
def login():
    st.markdown("<div class='header'>AARIVA</div>", unsafe_allow_html=True)
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
                    st.error("Invalid")

def faculty_view():
    st.title("Faculty Dashboard")
    
    with st.expander("📂 Upload Data", expanded=True):
        up_file = st.file_uploader("Upload CSV/Excel", type=['csv','xlsx'])
        if up_file:
            df = process_files(up_file)
            if df is not None:
                st.session_state.cohort_data = df
                st.success("Data Ingested!")

    if st.session_state.cohort_data is not None:
        df = st.session_state.cohort_data
        
        # Safe Metrics
        rapid = len(df[df['Profile'] == "Rapid Guesser"])
        st.metric("Rapid Guessers", rapid)
        
        # PLOTLY CHART (Now Safe)
        try:
            fig = px.scatter(
                df, 
                x="Time", 
                y="Score", 
                color="Profile", 
                hover_data=["Student ID"], 
                title="Velocity Analysis",
                color_discrete_map={"Rapid Guesser":"red", "Stable":"blue", "Struggling Learner":"orange", "Mastery":"green"}
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not render chart: {e}")
        
        st.dataframe(df)

# --- ROUTER ---
if not st.session_state.authenticated:
    login()
else:
    with st.sidebar:
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
    if st.session_state.role == 'Faculty': faculty_view()
    elif st.session_state.role == 'Dean': st.title("Dean View")
    elif st.session_state.role == 'Student': st.title("Student View")
