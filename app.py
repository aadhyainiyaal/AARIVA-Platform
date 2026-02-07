
import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import PyPDF2
import re
import hashlib
from datetime import datetime

st.set_page_config(page_title="AARIVA Enterprise", layout="wide", page_icon="🏛️")

# --- DATABASE SETUP ---
DB_FILE = "aariva_enterprise.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. USERS TABLE (The 8 Roles) - Using Double Quotes to avoid conflict
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT,
        fullname TEXT,
        student_id TEXT
    )""")
    
    # 2. COURSES TABLE
    c.execute("""CREATE TABLE IF NOT EXISTS courses (
        course_code TEXT PRIMARY KEY,
        course_name TEXT,
        lead_faculty TEXT
    )""")
    
    # 3. ASSESSMENTS TABLE (Metadata)
    c.execute("""CREATE TABLE IF NOT EXISTS assessments (
        assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        course_code TEXT,
        date_created TEXT
    )""")
    
    # 4. P-LENS RESULTS TABLE (The Algorithm Data)
    c.execute("""CREATE TABLE IF NOT EXISTS plens_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id INTEGER,
        student_id TEXT,
        score REAL,
        time_minutes REAL,
        category TEXT,
        risk_level TEXT,
        FOREIGN KEY(assessment_id) REFERENCES assessments(assessment_id)
    )""")
    
    # --- SEED DEFAULT USERS ---
    default_users = [
        ("admin", "admin2025", "Admin", "System Admin", None),
        ("dean", "dean2025", "Dean", "Dr. Dean of Medicine", None),
        ("director", "dir2025", "Program Director", "Program Director", None),
        ("lead", "lead2025", "Lead Faculty", "Dr. Sivapriya", None),
        ("faculty", "fac2025", "Faculty", "Faculty Member", None),
        ("grader", "grade2025", "Grader", "Teaching Assistant", None),
        ("mentor", "ment2025", "Mentor", "Academic Mentor", None),
        ("student", "learn2025", "Student", "Student User", "2025MI01")
    ]
    
    for u in default_users:
        try:
            c.execute("INSERT INTO users VALUES (?,?,?,?,?)", u)
        except sqlite3.IntegrityError: pass
        
    conn.commit()
    conn.close()

# Initialize immediately
if not os.path.exists(DB_FILE): init_db()
else: init_db()

# ==============================================================================
# LOGIC ENGINE
# ==============================================================================

def parse_time_str(t_str):
    if pd.isna(t_str): return 0
    t_str = str(t_str).strip().lower()
    try:
        if 'h' in t_str or 'm' in t_str:
            h, m = 0, 0
            clean = re.sub(r'[^0-9hm\s]', '', t_str)
            parts = clean.split(' ')
            for p in parts:
                if 'h' in p: h = int(p.replace('h',''))
                if 'm' in p: m = int(p.replace('m',''))
            return (h*60) + m
        return 0
    except: return 0

def process_and_save(pdf_file, time_file, assessment_name, course_code):
    # 1. PARSE PDF
    pdf_data = []
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        current_sid = None
        for page in reader.pages:
            text = page.extract_text()
            sid_search = re.search(r"StudentID:\s*(\S+)", text)
            if sid_search: current_sid = sid_search.group(1).strip()
            
            score_matches = re.findall(r"My Score\s*[\r\n]*\s*\(\s*(\d+)/30\s*\)", text)
            for score in score_matches:
                if current_sid and not any(d['StudentID'] == current_sid for d in pdf_data):
                    pdf_data.append({'StudentID': current_sid, 'Score': int(score)})
    except: return False, "PDF Error"

    # 2. PARSE CSV
    try:
        if time_file.name.endswith('.csv'): df_time = pd.read_csv(time_file)
        else: df_time = pd.read_excel(time_file)
        
        time_col = next((c for c in df_time.columns if 'total' in c.lower()), None)
        id_col = next((c for c in df_time.columns if 'id' in c.lower()), None)
        
        if not time_col: return False, "CSV Error: No Time Column"
        
        df_time['Total_Minutes'] = df_time[time_col].apply(parse_time_str)
        df_time['StudentID'] = df_time[id_col].astype(str).str.strip()
    except: return False, "CSV Error"

    # 3. MERGE
    df_scores = pd.DataFrame(pdf_data)
    df_scores['Match_ID'] = df_scores['StudentID'].str.lower().str.strip()
    df_time['Match_ID'] = df_time['StudentID'].str.lower().str.strip()
    
    merged = pd.merge(df_scores, df_time, on='Match_ID', how='inner')
    
    if merged.empty: return False, "No matching Student IDs found."

    # SAVE TO DB
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create Assessment
    c.execute("INSERT INTO assessments (name, course_code, date_created) VALUES (?,?,?)", 
              (assessment_name, course_code, str(datetime.now().date())))
    assessment_id = c.lastrowid
    
    # Insert Results
    count = 0
    for _, row in merged.iterrows():
        t = row['Total_Minutes']
        s = row['Score']
        
        # P-LENS Logic
        category = "Stable"
        risk = "Low"
        if t < 20 and s < 18: 
            category = "Rapid Guesser"
            risk = "High"
        elif t > 50 and s < 18:
            category = "Struggling Learner"
            risk = "Medium"
        elif t < 20 and s > 25:
            category = "Mastery"
            risk = "Low"
            
        c.execute("INSERT INTO plens_results (assessment_id, student_id, score, time_minutes, category, risk_level) VALUES (?,?,?,?,?,?)",
                  (assessment_id, row['StudentID_x'], s, t, category, risk))
        count += 1
        
    conn.commit()
    conn.close()
    return True, f"Saved {count} records to Assessment ID: {assessment_id}"

# ==============================================================================
# UI ROUTING
# ==============================================================================

if 'authenticated' not in st.session_state: st.session_state.authenticated = False

def login_screen():
    st.markdown("<h1 style='color:#2E86C1; text-align:center;'>AARIVA Enterprise</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT role, fullname, student_id FROM users WHERE username=? AND password=?", (u, p))
                user = c.fetchone()
                conn.close()
                if user:
                    st.session_state.authenticated = True
                    st.session_state.role = user[0]
                    st.session_state.name = user[1]
                    st.session_state.sid = user[2]
                    st.rerun()
                else:
                    st.error("Invalid Credentials")

def dean_dashboard():
    st.title("🏛️ Dean's Executive Dashboard")
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM plens_results", conn)
    conn.close()
    
    if not df.empty:
        rapid = len(df[df['category'] == "Rapid Guesser"])
        struggle = len(df[df['category'] == "Struggling Learner"])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Assessments Processed", len(df))
        c2.metric("Rapid Guessers (Risk)", rapid, delta="Action Needed", delta_color="inverse")
        c3.metric("Struggling Learners", struggle)
        
        fig = px.pie(df, names='category', title="Institutional Learning Behaviors")
        st.plotly_chart(fig)
    else:
        st.info("No data yet.")

def faculty_dashboard():
    st.title("👨‍🏫 Faculty Command Center")
    
    with st.expander("📝 Create Assessment", expanded=True):
        c1, c2 = st.columns(2)
        a_name = c1.text_input("Name", "Mid-Sem Fall 2025")
        c_code = c2.text_input("Course", "ITH-101")
        f_pdf = st.file_uploader("PDF Report", type=['pdf'])
        f_time = st.file_uploader("Time Log", type=['csv', 'xlsx'])
        
        if st.button("Run P-LENS & Save"):
            if f_pdf and f_time:
                success, msg = process_and_save(f_pdf, f_time, a_name, c_code)
                if success: st.success(msg)
                else: st.error(msg)
            else:
                st.warning("Upload both files.")

    st.markdown("---")
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM plens_results ORDER BY id DESC", conn)
    conn.close()
    
    if not df.empty:
        fig = px.scatter(df, x="time_minutes", y="score", color="category",
                         title="Live Velocity Matrix",
                         color_discrete_map={"Rapid Guesser": "red", "Stable": "blue", "Mastery":"green"})
        fig.add_vline(x=20, line_dash="dash", line_color="gray")
        st.plotly_chart(fig)

def student_dashboard():
    st.title(f"🎓 Student Portal | {st.session_state.name}")
    my_id = st.session_state.sid
    
    if not my_id:
        st.warning("No Student ID linked.")
        return

    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM plens_results WHERE student_id=?", conn, params=(my_id,))
    conn.close()
    
    if not df.empty:
        row = df.iloc[-1]
        cat = row['category']
        if cat == "Rapid Guesser":
             st.error("⚠️ Alert: Rapid Guessing Detected. Please slow down.")
        elif cat == "Struggling Learner":
             st.warning("⚠️ Alert: High Effort, Low Score.")
        else:
             st.success("✅ On Track.")
        st.dataframe(df)
    else:
        st.info("No results found.")

# ROUTING
if not st.session_state.authenticated:
    login_screen()
else:
    with st.sidebar:
        st.write(f"User: {st.session_state.name}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()

    r = st.session_state.role
    if r == "Admin": st.title("🛠️ Admin Panel")
    elif r in ["Dean", "Program Director"]: dean_dashboard()
    elif r in ["Faculty", "Lead Faculty", "Grader", "Mentor"]: faculty_dashboard()
    elif r == "Student": student_dashboard()
