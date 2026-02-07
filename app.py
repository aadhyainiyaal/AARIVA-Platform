
import streamlit as st
import pandas as pd
import time
import random

# --- 1. CONFIGURATION & BRANDING ---
st.set_page_config(page_title="AARIVA Platform", layout="wide", page_icon="🧠")

# Custom CSS for Branding
st.markdown("""
    <style>
    .main-title {font-size: 3.5rem; color: #2E86C1; text-align: center; font-weight: 800;}
    .sub-title {font-size: 1.2rem; color: #555; text-align: center; font-style: italic;}
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f1f1f1; 
             color: #333; text-align: center; padding: 10px; font-size: 0.8rem; border-top: 1px solid #ddd;}
    </style>
""", unsafe_allow_html=True)

# --- 2. SESSION STATE (The Memory) ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'role' not in st.session_state: st.session_state.role = None
if 'cohort_data' not in st.session_state: st.session_state.cohort_data = None

# --- 3. DATABASE (Simulated for Beta) ---
USERS = {
    "prof": {"pass": "admin123", "role": "Faculty", "name": "Dr. Sivapriya"},
    "dean": {"pass": "dean2025", "role": "Dean", "name": "Director of Medical Ed"},
    "student": {"pass": "learn2025", "role": "Student", "name": "Student User"}
}

# --- 4. THE LOGIC ENGINE (Stealth Assessment) ---
def analyze_student_behavior(score, time_minutes, class_avg_time=35):
    # THE RULES (Based on Thesis Hypothesis)
    if time_minutes < (class_avg_time * 0.6) and score < 60:
        return "Rapid Guesser", "⚠️ High Risk: Disengagement", "Velocity Alert: You are moving too fast. Please use the 2-pass strategy."
    elif time_minutes > (class_avg_time * 1.3) and score < 60:
        return "Struggling Learner", "⚠️ Needs Academic Support", "High Effort Detected. We recommend scheduling a tutor session for this topic."
    elif time_minutes < (class_avg_time * 0.7) and score > 85:
        return "Mastery", "✅ High Performer", "Excellent Efficiency. Consider peer-teaching."
    else:
        return "Consistent", "✅ Stable", "Maintain current study pace."

# --- 5. VIEWS (The Roles) ---

def login_screen():
    st.markdown("<div class='main-title'>AARIVA</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Adaptive Analytics for Real-time Intelligent Velocity Assessment</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Enter System"):
                if u in USERS and USERS[u]['pass'] == p:
                    st.session_state.authenticated = True
                    st.session_state.role = USERS[u]['role']
                    st.session_state.user_name = USERS[u]['name']
                    st.rerun()
                else:
                    st.error("Invalid Credentials")

def faculty_dashboard():
    st.title(f"👨‍🏫 Faculty Command Center | {st.session_state.user_name}")
    
    tab1, tab2 = st.tabs(["📥 Data Ingestion", "📊 Risk Matrix"])
    
    with tab1:
        st.info("Upload ExamSoft Reports (PDF) and Moodle Logs (Excel)")
        # In Reality, we enable file uploaders here. For the Demo, we use a Generator.
        if st.button("🔄 Import Latest Exam Data (Simulation)"):
            with st.spinner("Processing Stealth Metrics..."):
                time.sleep(1.5)
                # GENERATE REALISTIC DATA
                data = []
                for i in range(1, 31):
                    sid = f"2025MI{i:02d}"
                    # Create some Rapid Guessers
                    if i < 5: 
                        t, s = 12, random.randint(30, 50) # Fast & Fail
                    # Create some Strugglers
                    elif i > 25:
                        t, s = 55, random.randint(40, 55) # Slow & Fail
                    # Create Normals
                    else:
                        t, s = random.randint(25, 45), random.randint(65, 95)
                        
                    profile, risk, nudge = analyze_student_behavior(s, t)
                    data.append([sid, t, s, profile, risk, nudge])
                
                df = pd.DataFrame(data, columns=["Student ID", "Time (m)", "Score", "Behavior Profile", "Risk Level", "Intervention"])
                st.session_state.cohort_data = df
                st.success(f"Successfully analyzed {len(df)} students.")
                
    with tab2:
        if st.session_state.cohort_data is not None:
            df = st.session_state.cohort_data
            
            # Metrics
            rapid = len(df[df['Behavior Profile'] == "Rapid Guesser"])
            struggle = len(df[df['Behavior Profile'] == "Struggling Learner"])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Rapid Guessers (Disengaged)", rapid, delta="Urgent Intervention Needed", delta_color="inverse")
            c2.metric("Struggling Learners", struggle, delta="Needs Tutoring")
            c3.metric("Cohort Size", len(df))
            
            st.markdown("### 🚨 Intervention Queue")
            # Style the dataframe
            def highlight_risk(val):
                color = '#ffcccc' if 'High Risk' in val else '#fff4cc' if 'Needs' in val else 'white'
                return f'background-color: {color}'
            
            st.dataframe(df.style.applymap(highlight_risk, subset=['Risk Level']))
            
            if st.button("📧 Send Nudges to At-Risk Students"):
                st.toast(f"Sent {rapid + struggle} personalized emails based on Behavior Profiles!", icon="🚀")

def dean_dashboard():
    st.title("🏛️ Institutional Oversight Dashboard")
    st.markdown("### Longitudinal Burnout Trends (2021-2025)")
    st.line_chart({"2021": 15, "2022": 18, "2023": 22, "2024": 19, "2025": 14})
    st.caption("Percentage of cohort exhibiting 'Rapid Guessing' behavior (Indicator of Burnout).")

def student_dashboard():
    st.title("🧠 My AARIVA Profile")
    st.info("AARIVA helps you optimize your exam strategy: Balancing Speed vs. Accuracy.")
    
    if st.session_state.cohort_data is not None:
        # Simulate the student is "2025MI02" (A Rapid Guesser from our logic above)
        my_id = "2025MI02" 
        st.write(f"Logged in as: **{my_id}**")
        
        row = st.session_state.cohort_data[st.session_state.cohort_data['Student ID'] == my_id]
        if not row.empty:
            risk = row.iloc[0]['Risk Level']
            nudge = row.iloc[0]['Intervention']
            
            st.markdown("---")
            if "High Risk" in risk:
                st.error(f"**Status:** {risk}")
                st.markdown(f"### 💡 AARIVA Coach Says:")
                st.markdown(f"> *{nudge}*")
            else:
                st.success("You are on track!")
    else:
        st.warning("No assessment data available yet.")

# --- 6. MAIN ROUTING ---
if not st.session_state.authenticated:
    login_screen()
else:
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user_name}**")
        if st.button("Log Out"):
            st.session_state.authenticated = False
            st.rerun()
            
    if st.session_state.role == "Faculty": faculty_dashboard()
    elif st.session_state.role == "Dean": dean_dashboard()
    elif st.session_state.role == "Student": student_dashboard()

# --- 7. FOOTER ---
st.markdown("<div class='footer'>AARIVA v1.0 | Developed by A. Iniyaal & Sivapriya Research Group</div>", unsafe_allow_html=True)
