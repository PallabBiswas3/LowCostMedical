import os
import streamlit as st
import smtplib
from email.message import EmailMessage
from PyPDF2 import PdfMerger
import psycopg2
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from datetime import datetime
from fpdf import FPDF
import time
import bcrypt

st.set_page_config(
    page_title="MedReport IIT KGP",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    .main .block-container { padding: 1.5rem 2rem 3rem; max-width: 1200px; }
    :root {
        --primary: #1a6fd4; --primary-d: #1459ad; --accent: #0fd9a0;
        --danger: #e84f4f; --warn: #f0a940; --bg: #f0f4fb; --card: #ffffff;
        --border: #dde3f0; --text: #1c2b45; --muted: #6b7a99; --sidebar-bg: #0f1c35;
    }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
    .stApp { background: var(--bg); }
    section[data-testid="stSidebar"] { background: var(--sidebar-bg) !important; border-right: none !important; }
    section[data-testid="stSidebar"] * { color: #c8d6f0 !important; }
    section[data-testid="stSidebar"] h3 { color: #ffffff !important; }
    section[data-testid="stSidebar"] hr { border-color: #2a3d60 !important; }
    .page-title { font-size: 1.75rem; font-weight: 700; color: var(--text); margin-bottom: 0.15rem; }
    .page-subtitle { color: var(--muted); font-size: 0.9rem; margin-bottom: 1.5rem; }
    .section-title { font-size: 1rem; font-weight: 600; color: var(--primary); letter-spacing: .4px;
        margin-bottom: 1rem; display: flex; align-items: center; gap: 8px; }
    .section-title span.icon { background: #e8f1fd; border-radius: 8px; padding: 4px 8px; font-size: 1rem; }
    .stApp { background: var(--bg); }
    .stButton > button { border-radius: 8px !important; font-weight: 600 !important;
        font-size: 0.875rem !important; padding: .55rem 1.25rem !important;
        transition: all .2s ease !important; border: none !important; }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1a6fd4, #0fd9a0) !important;
        color: white !important; box-shadow: 0 4px 14px rgba(26,111,212,.3) !important; }
    .stButton > button[kind="primary"]:hover { transform: translateY(-1px) !important;
        box-shadow: 0 6px 18px rgba(26,111,212,.4) !important; }
    .stButton > button[kind="secondary"] { background: white !important;
        border: 1.5px solid var(--border) !important; color: var(--text) !important; }
    .stButton > button[kind="secondary"]:hover { border-color: var(--primary) !important; color: var(--primary) !important; }
    .stTextInput > div > div > input, .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 8px !important; border: 1.5px solid var(--border) !important;
        font-size: 0.875rem !important; background: #fafbff !important; }
    .stTextInput > div > div > input:focus, .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--primary) !important; box-shadow: 0 0 0 3px rgba(26,111,212,.1) !important; }
    .stRadio > div > label { background: #fafbff !important; border: 1.5px solid var(--border) !important;
        border-radius: 8px !important; padding: .35rem .75rem !important; font-size: 0.85rem !important; transition: all .15s ease; }
    .stRadio > div > label:has(input:checked) { border-color: var(--primary) !important;
        background: #e8f1fd !important; color: var(--primary) !important; font-weight: 600 !important; }
    .stAlert { border-radius: 10px !important; font-size: 0.875rem !important; }
    .success-banner { background: linear-gradient(135deg, #0f3460, #1a6fd4); color: white;
        border-radius: 16px; padding: 2rem 2.5rem; text-align: center; margin: 1rem 0 1.5rem; }
    .success-banner h2 { font-size: 1.5rem; margin: .5rem 0 .25rem; }
    .success-banner p { opacity: .8; font-size: .9rem; }
    .badge { display: inline-block; padding: .2rem .65rem; border-radius: 20px;
        font-size: .72rem; font-weight: 600; letter-spacing: .4px; }
    .badge-blue { background: #dbeafe; color: #1d4ed8; }
    .badge-green { background: #d1fae5; color: #065f46; }
    .badge-red { background: #fee2e2; color: #991b1b; }
    .badge-yellow { background: #fef3c7; color: #92400e; }
    #MainMenu, footer, header { visibility: hidden; }
    div[data-testid="stHorizontalBlock"] { gap: 1.25rem !important; }
    </style>
    """, unsafe_allow_html=True)

# ── Secrets ──
DB_URL = st.secrets["DATABASE_URL"]
SMTP_HOST = st.secrets["SMTP_HOST"]
SMTP_PORT = int(st.secrets["SMTP_PORT"])
SMTP_USER = st.secrets["SMTP_USER"]
SMTP_PASS = st.secrets["SMTP_PASS"]
GOOGLE_SHEET_NAME = st.secrets["GOOGLE_SHEET_NAME"]
GOOGLE_SERVICE_ACCOUNT_INFO = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]

# ── Google Sheets ──
sheet = None
sheet_init_error = None
try:
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_SERVICE_ACCOUNT_INFO, scope)
    client = gspread.authorize(creds)
    sheet = client.open(GOOGLE_SHEET_NAME).sheet1
except Exception as e:
    sheet_init_error = str(e)

# ── DB ──
def get_db():
    return psycopg2.connect(DB_URL, sslmode="require")

def init_db():
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS responses (
            id SERIAL PRIMARY KEY, patient_id INTEGER, report_id INTEGER,
            collection_date DATE, report_date DATE, patient_name VARCHAR(100),
            patient_age INTEGER, patient_gender VARCHAR(10), patient_referee VARCHAR(100),
            patient_phone VARCHAR(20), weight NUMERIC(7,2), height NUMERIC(7,2),
            bmi NUMERIC(7,2), pulse_rate INTEGER, systolic_blood_pressure NUMERIC(20),
            diastolic_blood_pressure NUMERIC(20), o2_level NUMERIC(10), temperature NUMERIC(7,2),
            vision VARCHAR(50), breathing TEXT, hearing TEXT, skin_condition TEXT,
            oral_health TEXT, urine_color TEXT, hair_loss TEXT, nail_changes TEXT,
            cataract TEXT, disabilities TEXT, hemoglobin_level NUMERIC(5,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        conn.commit(); conn.close()
    except Exception as e:
        st.error(f"DB init error: {e}")

def get_next_patient_id():
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(patient_id),0)+1 FROM responses")
        n = cur.fetchone()[0]; conn.close(); return n or 1
    except: return 1

def get_next_report_id():
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(report_id),0)+1 FROM responses")
        n = cur.fetchone()[0]; conn.close(); return n or 1001
    except: return 1001

def authenticate(username, password):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username=%s",(username,))
        row = cur.fetchone(); conn.close()
        if not row: return False
        return bcrypt.checkpw(password.encode(), row[0].encode())
    except: return False

def register_user(username, password):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE username=%s",(username,))
        if cur.fetchone(): return False,"Username already exists"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur.execute("INSERT INTO users (username,password) VALUES (%s,%s)",(username,hashed))
        conn.commit(); conn.close(); return True,"Account created!"
    except Exception as e: return False,str(e)

# ── Utilities ──
def parse_date(d):
    if not d: return None
    if isinstance(d, datetime): return d.date()
    for fmt in ("%Y-%m-%d","%d-%m-%Y","%d/%m/%Y"):
        try: return datetime.strptime(d,fmt).date()
        except: pass
    return None

def calculate_bmi(weight, height):
    try:
        w,h = float(weight),float(height)
        return round(w/(h/100)**2,1) if h else None
    except: return None

def bmi_category(bmi):
    if bmi is None: return "—","muted"
    b = float(bmi)
    if b < 18.5: return "Underweight","warn"
    if b < 25: return "Normal","ok"
    if b < 30: return "Overweight","warn"
    return "Obese","danger"

def analyze_numerical_vitals(data):
    c = []
    bmi = data.get('bmi')
    if bmi:
        b = float(bmi)
        if b < 18.5: c.append("The patient is underweight")
        elif b >= 25 and b < 30: c.append("The patient is overweight")
        elif b >= 30: c.append("The patient is obese")
    s,d = data.get('systolic_blood_pressure'),data.get('diastolic_blood_pressure')
    if s and d:
        if int(s)<90 or int(d)<60: c.append("The patient has low blood pressure")
        elif int(s)>120 or int(d)>80: c.append("The patient has high blood pressure")
    t = data.get('temperature')
    if t:
        tv = float(t)
        if tv<97.8: c.append("The patient has a low body temperature")
        elif tv>99.1: c.append("The patient has a fever")
    sp = data.get('o2_level')
    if sp and float(str(sp).replace('%','').strip())<94:
        c.append("The patient has low SpO2 (possible hypoxemia)")
    p = data.get('pulse_rate')
    if p:
        pv = float(p)
        if pv<60: c.append("The patient has bradycardia (low pulse rate)")
        elif pv>100: c.append("The patient has tachycardia (high pulse rate)")
    return c

def analyze_subjective_answers(data):
    c = []
    hl = data.get('hair_loss','')
    if hl=="Yes, severe hair loss": c.append("The doctor needs to urgently look at the patient's hair condition.")
    elif "mild" in hl or "moderate" in hl: c.append("Deeper inspection is required for the patient's hair condition.")
    nc = data.get('nail_changes','')
    if nc=="Yes, dark streaks": c.append("The doctor needs to urgently look at the patient's nail condition.")
    elif nc in ["Yes, white spots","Yes, yellowing"]: c.append("Deeper inspection is required for the patient's nail condition.")
    uc = data.get('urine_color','')
    if "Brownish" in uc: c.append("The doctor needs to urgently look at the patient's urinary condition.")
    elif uc=="Dark yellow": c.append("Urinary condition may depict an underlying symptom.")
    oh = data.get('oral_health','')
    if oh in ["Bleeding gums","Frequent mouth ulcers"]: c.append("The doctor needs to urgently look at the patient's mouth condition.")
    elif oh in ["Bad breath","Tooth pain or sensitivity"]: c.append("Mouth condition may depict an underlying symptom.")
    return c

# ── PDF ──
class PDF(FPDF):
    def header(self):
        self.set_draw_color(0,0,0); self.rect(5,5,200,287)
        if os.path.exists("assets/kgp_logo.png"): self.image("assets/kgp_logo.png",10,8,25)
        self.set_font('Times','B',16); self.set_xy(0,10)
        self.cell(0,10,"Indian Institute of Technology Kharagpur",0,1,'C')
        self.set_font('Times','B',14)
        self.cell(0,10,"Solar-Powered Mobile Health Measurement Device",0,1,'C'); self.ln(8)
    def footer(self):
        self.set_y(-20); self.set_font('Times','I',10)
        self.cell(0,10,'~ End of Report ~',0,0,'C')
    def patient_info(self,l,r):
        self.set_font('Times','',10); iy=self.get_y()
        self.multi_cell(95,7,"\n".join(f"{k}: {v}" for k,v in l.items()),0,'L')
        self.set_y(iy); self.set_x(105)
        self.multi_cell(95,7,"\n".join(f"{k}: {v}" for k,v in r.items()),0,'L')
        self.line(10,self.get_y(),200,self.get_y()); self.ln(6)
    def add_dates(self,l,r):
        self.set_font('Times','',10); iy=self.get_y()
        self.multi_cell(95,7,"\n".join(f"{k}: {v}" for k,v in l.items()),0,'L')
        self.set_y(iy); self.set_x(105)
        self.multi_cell(95,7,"\n".join(f"{k}: {v}" for k,v in r.items()),0,'L')
        self.ln(6); self.line(10,self.get_y(),200,self.get_y())
    def chapter_title(self,t):
        self.set_font('Times','B',12); self.cell(0,8,t,0,1,'L'); self.ln(4)
    def test_table_1(self,rows):
        self.set_font('Times','B',10); cw=[60,40,50,40]
        for i,h in enumerate(['VITALS','RESULT','REF. RANGE','UNIT']): self.cell(cw[i],7,h,1,0,'C')
        self.ln(); self.set_font('Times','',9)
        for r in rows:
            self.cell(cw[0],7,r['description'],1); self.cell(cw[1],7,str(r.get('result','')),1)
            self.cell(cw[2],7,r.get('range',''),1); self.cell(cw[3],7,r.get('unit',''),1); self.ln()
    def test_table_2(self,rows):
        self.set_font('Times','B',10); cw=[20,120,50]
        for i,h in enumerate(['Sl.No','QUESTIONS','RESPONSE']): self.cell(cw[i],7,h,1,0,'C')
        self.ln(); self.set_font('Times','',9)
        for i,r in enumerate(rows):
            self.cell(cw[0],7,str(i+1)+'.',1,align='C')
            self.cell(cw[1],7,r.get('description',''),1); self.cell(cw[2],7,str(r.get('result','')),1); self.ln()
    def add_comments(self,text):
        self.set_font('Times','B',12); self.cell(0,10,'Comments:',0,1)
        self.set_font('Times','',11); self.multi_cell(0,6,text)

def create_medical_report(data):
    os.makedirs("generated_files",exist_ok=True)
    pdf=PDF(); pdf.add_page()
    pdf.add_dates({'Collection Date':data.get('collection_date','')},{'Report Date':data.get('report_date','')})
    pdf.patient_info(
        {'Name':data.get('patient_name',''),'Age':data.get('patient_age',''),
         'Gender':data.get('patient_gender',''),'Referred By':data.get('patient_referee','')},
        {'Contact':data.get('patient_phone',''),'Patient ID':str(data.get('patient_ID','')),
         'Report ID':str(data.get('report_ID',''))})
    pdf.chapter_title('Body Vitals')
    bmi=data.get('bmi') or calculate_bmi(data.get('weight'),data.get('height'))
    data['bmi']=bmi
    pdf.test_table_1([
        {'description':'Weight','result':f"{data.get('weight','')} kg",'range':'-','unit':'kg'},
        {'description':'Height','result':f"{data.get('height','')} cm",'range':'-','unit':'cm'},
        {'description':'BMI','result':bmi or '','range':'18.5-24.9','unit':'kg/m²'},
        {'description':'SpO2','result':data.get('o2_level',''),'range':'94-100%','unit':'%'},
        {'description':'Temperature','result':f"{data.get('temperature','')}°F",'range':'97.8-99.1','unit':'°F'},
        {'description':'Pulse Rate','result':f"{data.get('pulse_rate','')} bpm",'range':'60-100','unit':'bpm'},
        {'description':'Systolic BP','result':data.get('systolic_blood_pressure',''),'range':'90-140','unit':'mmHg'},
        {'description':'Diastolic BP','result':data.get('diastolic_blood_pressure',''),'range':'60-140','unit':'mmHg'},
        {'description':'Hemoglobin','result':f"{data.get('hemoglobin_level','')} g/dL",'range':'12.0-15.5','unit':'g/dL'},
    ])
    pdf.chapter_title('General Health Questions')
    pdf.test_table_2([
        {'description':"Can you see clearly without glasses?",'result':data.get('vision','')},
        {'description':"Do you experience difficulty in breathing?",'result':data.get('breathing','')},
        {'description':"Do you have any difficulty in hearing?",'result':data.get('hearing','')},
        {'description':"Do you have any visible skin conditions?",'result':data.get('skin_condition','')},
        {'description':"Do you experience any mouth conditions?",'result':data.get('oral_health','')},
        {'description':"What is your usual urine colour?",'result':data.get('urine_color','')},
        {'description':"Have you noticed significant hair loss recently?",'result':data.get('hair_loss','')},
        {'description':"Have you noticed any unusual changes in your nail colour?",'result':data.get('nail_changes','')},
        {'description':"Have you been diagnosed with or noticed signs of cataract?",'result':data.get('cataract','')},
        {'description':"Do you have any physical disabilities?",'result':data.get('disabilities','')},
    ])
    all_c = analyze_numerical_vitals(data)+analyze_subjective_answers(data)
    if all_c: pdf.add_comments(". ".join(all_c)+".")
    out="generated_files/medical_report.pdf"; pdf.output(out); return out

def save_response(data):
    conn=None
    try:
        conn=get_db(); cur=conn.cursor()
        pid=get_next_patient_id(); rid=get_next_report_id()
        cols=["patient_id","report_id","collection_date","report_date","patient_name",
              "patient_age","patient_gender","patient_referee","patient_phone","weight","height",
              "bmi","pulse_rate","systolic_blood_pressure","diastolic_blood_pressure","o2_level",
              "temperature","vision","breathing","hearing","skin_condition","oral_health",
              "urine_color","hair_loss","nail_changes","cataract","disabilities","hemoglobin_level"]
        vals=[pid,rid]
        for c in cols[2:]:
            if c in ("collection_date","report_date"): vals.append(parse_date(data.get(c)))
            else: vals.append(data.get(c))
        data['patient_ID']=pid; data['report_ID']=rid
        sql=f"INSERT INTO responses ({', '.join(cols)}) VALUES ({', '.join(['%s']*len(cols))})"
        cur.execute(sql,tuple(vals)); conn.commit()
    except Exception as e:
        if conn: conn.rollback(); raise
    finally:
        if conn: conn.close()

def save_to_google_sheets(data):
    if not sheet: return False
    try:
        records=sheet.get_all_records()
        if not records: sheet.append_row(list(data.keys())); records=[]
        headers=list(records[0].keys()) if records else list(data.keys())
        row=[str(data.get(h,'')) for h in headers]
        sheet.append_row(row); return True
    except: return False

def send_email(recipient,subject,body,attachment_path,fname="medical_report.pdf"):
    msg=EmailMessage(); msg["Subject"]=subject; msg["From"]=SMTP_USER; msg["To"]=recipient
    msg.set_content(body)
    with open(attachment_path,"rb") as f:
        msg.add_attachment(f.read(),maintype="application",subtype="pdf",filename=fname)
    with smtplib.SMTP(SMTP_HOST,SMTP_PORT) as srv:
        srv.starttls(); srv.login(SMTP_USER,SMTP_PASS); srv.send_message(msg)

def full_reset():
    auth=st.session_state.get('authenticated',False)
    st.session_state.clear()
    st.session_state.authenticated=auth
    st.session_state.current_page="generate_report"

# ── LOGIN PAGE ──
def login_page():
    inject_css()
    st.markdown("""
    <div style="text-align:center;padding-top:2.5rem;">
        <div style="display:inline-block;background:linear-gradient(135deg,#1a6fd4,#0fd9a0);
            border-radius:18px;padding:16px 20px;margin-bottom:.75rem;">
            <span style="font-size:2.2rem;">🏥</span></div>
        <h1 style="font-size:1.7rem;font-weight:700;color:#1c2b45;margin:.5rem 0 .2rem;">MedReport</h1>
        <p style="color:#6b7a99;font-size:.875rem;margin:0;">IIT Kharagpur · Solar Health Device</p>
    </div>""", unsafe_allow_html=True)

    _,col,_ = st.columns([1,1.3,1])
    with col:
        st.markdown("<div style='height:1.25rem'></div>",unsafe_allow_html=True)
        tab = st.radio("",["Sign In","Create Account"],horizontal=True,label_visibility="collapsed")

        if tab=="Sign In":
            with st.form("login_form"):
                st.markdown("#### Welcome back")
                u=st.text_input("Username",placeholder="Your username")
                p=st.text_input("Password",type="password",placeholder="Your password")
                st.markdown("<div style='height:.4rem'></div>",unsafe_allow_html=True)
                if st.form_submit_button("Sign In →",type="primary",use_container_width=True):
                    if authenticate(u,p):
                        st.session_state.authenticated=True
                        st.session_state.current_page="generate_report"
                        st.balloons(); st.rerun()
                    else:
                        st.error("Invalid username or password.")
        else:
            with st.form("reg_form"):
                st.markdown("#### Create your account")
                u=st.text_input("Username",placeholder="Choose a username")
                p=st.text_input("Password",type="password",placeholder="Choose a password")
                cp=st.text_input("Confirm Password",type="password",placeholder="Repeat password")
                st.markdown("<div style='height:.4rem'></div>",unsafe_allow_html=True)
                if st.form_submit_button("Create Account →",type="primary",use_container_width=True):
                    if not u or not p: st.error("Please fill in all fields.")
                    elif p!=cp: st.error("Passwords do not match.")
                    else:
                        ok,msg=register_user(u,p)
                        if ok: st.success(f"✅ {msg} — please sign in."); st.balloons()
                        else: st.error(f"❌ {msg}")

    st.markdown("""<div style="text-align:center;margin-top:3rem;color:#6b7a99;font-size:.75rem;">
        © IIT Kharagpur · Solar-Powered Mobile Health Measurement Device</div>""",unsafe_allow_html=True)

# ── SIDEBAR ──
def render_sidebar(data_snapshot=None):
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:1.25rem 0 .5rem;">
            <div style="background:linear-gradient(135deg,#1a6fd4,#0fd9a0);border-radius:14px;
                display:inline-block;padding:12px 16px;margin-bottom:.75rem;">
                <span style="font-size:1.75rem;">🏥</span></div>
            <h3 style="color:#ffffff !important;margin:0;font-size:1rem;">MedReport</h3>
            <p style="color:#8fa8c8 !important;font-size:.75rem;margin:.2rem 0 0;">IIT Kharagpur</p>
        </div>""",unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("<p style='color:#8fa8c8 !important;font-size:.7rem;font-weight:600;letter-spacing:.8px;text-transform:uppercase;'>Actions</p>",unsafe_allow_html=True)
        if st.button("＋  New Report",use_container_width=True,type="primary"):
            full_reset(); st.rerun()
        if st.button("↺  Refresh",use_container_width=True,type="secondary"):
            st.rerun()
        st.markdown("---")
        if data_snapshot:
            bmi=data_snapshot.get('bmi'); cat,_=bmi_category(bmi)
            pulse=data_snapshot.get('pulse_rate',0); spo2=data_snapshot.get('o2_level',0)
            st.markdown("<p style='color:#8fa8c8 !important;font-size:.7rem;font-weight:600;letter-spacing:.8px;text-transform:uppercase;'>Live Vitals</p>",unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#1a2d50;border-radius:10px;padding:1rem;margin-bottom:.75rem;">
                <div style="display:flex;justify-content:space-between;margin-bottom:.5rem;">
                    <span style="color:#8fa8c8;font-size:.75rem;">BMI</span>
                    <span style="color:#fff;font-weight:700;font-size:.9rem;">{bmi or '—'} ({cat})</span></div>
                <div style="display:flex;justify-content:space-between;margin-bottom:.5rem;">
                    <span style="color:#8fa8c8;font-size:.75rem;">Pulse</span>
                    <span style="color:#fff;font-weight:700;font-size:.9rem;">{pulse} bpm</span></div>
                <div style="display:flex;justify-content:space-between;">
                    <span style="color:#8fa8c8;font-size:.75rem;">SpO₂</span>
                    <span style="color:#0fd9a0;font-weight:700;font-size:.9rem;">{spo2}%</span></div>
            </div>""",unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("<p style='color:#8fa8c8 !important;font-size:.7rem;font-weight:600;letter-spacing:.8px;text-transform:uppercase;'>Support</p>",unsafe_allow_html=True)
        st.markdown("<p style='color:#8fa8c8 !important;font-size:.78rem;'>support@iitkharagpur.ac.in</p>",unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🚪  Logout",use_container_width=True,type="secondary"):
            st.session_state.authenticated=False; st.session_state.current_page="login"; st.rerun()

# ── SUCCESS SCREEN ──
def success_screen(data):
    render_sidebar()
    st.markdown("""
    <div class="success-banner">
        <div style="font-size:2.5rem;margin-bottom:.5rem;">✅</div>
        <h2>Report Generated Successfully</h2>
        <p>The medical diagnostic report is ready for download or delivery.</p>
    </div>""",unsafe_allow_html=True)
    bmi=data.get('bmi'); cat,_=bmi_category(bmi)
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Patient",data.get('patient_name','—'))
    c2.metric("BMI",f"{bmi or '—'} ({cat})")
    c3.metric("SpO₂",f"{data.get('o2_level','—')}%")
    c4.metric("Pulse",f"{data.get('pulse_rate','—')} bpm")
    st.markdown("---")
    fp=st.session_state.get('final_pdf')
    col_dl,col_em,col_new=st.columns([2,1.5,1.5])
    with col_dl:
        if fp and os.path.exists(fp):
            with open(fp,"rb") as f:
                st.download_button("⬇️  Download PDF Report",data=f,
                    file_name=f"report_{data.get('patient_name','patient').replace(' ','_')}.pdf",
                    mime="application/pdf",type="primary",use_container_width=True)
    with col_em:
        if st.button("📧  Email Report",use_container_width=True,type="secondary"):
            st.session_state.show_email_modal=True
    with col_new:
        if st.button("＋  New Report",use_container_width=True,type="secondary"):
            full_reset(); st.rerun()
    if st.session_state.get('show_email_modal'):
        st.markdown("---"); st.markdown("#### 📧 Send Report by Email")
        with st.form("email_form"):
            recipient=st.text_input("Recipient email",value=data.get('email',''))
            note=st.text_area("Message","Please find your medical diagnostic report attached.")
            ec1,ec2=st.columns(2)
            with ec1:
                if st.form_submit_button("Send ✉️",type="primary"):
                    if recipient:
                        try:
                            send_email(recipient,f"Medical Report – {data.get('patient_name','')}",note,fp)
                            st.success(f"✅ Report sent to {recipient}")
                            st.session_state.show_email_modal=False
                        except Exception as e: st.error(f"Email failed: {e}")
                    else: st.warning("Enter a recipient email.")
            with ec2:
                if st.form_submit_button("Cancel"):
                    st.session_state.show_email_modal=False; st.rerun()

# ── MAIN FORM PAGE ──
def report_generation_page():
    inject_css()
    if st.session_state.get('report_generated') and st.session_state.get('report_data'):
        success_screen(st.session_state['report_data']); return
    render_sidebar()
    st.markdown('<p class="page-title">📋 Medical Diagnostic Report Generator</p>',unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Complete all sections, then click <strong>Generate Report</strong>.</p>',unsafe_allow_html=True)

    with st.form("main_form"):
        # ── Section 1: Patient Info ──────────────────
        st.markdown('<div class="section-title"><span class="icon">👤</span> Patient Information</div>',unsafe_allow_html=True)
        r1,r2,r3=st.columns(3)
        with r1:
            patient_name=st.text_input("Full Name *",value="John Doe")
            patient_gender=st.selectbox("Gender",["Male","Female","Other"])
        with r2:
            patient_age=st.number_input("Age",0,150,30)
            patient_phone=st.text_input("Phone Number",value="9876543210")
        with r3:
            patient_referee=st.text_input("Referred By",value="Dr. Smith")
            email=st.text_input("Email (for delivery)",placeholder="patient@example.com")
        d1,d2,d3,d4=st.columns(4)
        with d1: collection_date=st.date_input("Collection Date",value=datetime.now().date())
        with d2: report_date=st.date_input("Report Date",value=datetime.now().date())
        with d3: report_ID=int(st.number_input("Report ID",0,value=get_next_report_id()))
        with d4: patient_ID=int(st.number_input("Patient ID",0,value=get_next_patient_id()))

        st.markdown("<hr style='border-color:#dde3f0;margin:1rem 0 1.25rem;'>",unsafe_allow_html=True)

        # ── Section 2: Vitals ──────────────────────
        st.markdown('<div class="section-title"><span class="icon">💓</span> Body Vitals</div>',unsafe_allow_html=True)
        v1,v2,v3,v4=st.columns(4)
        with v1:
            weight=st.number_input("Weight (kg)",0.0,300.0,70.0,step=0.5)
            height=st.number_input("Height (cm)",0.0,250.0,170.0,step=0.5)
        with v2:
            temperature=st.number_input("Temperature (°F)",90.0,115.0,98.6,step=0.1)
            pulse_rate=int(st.number_input("Pulse Rate (bpm)",0,300,72))
        with v3:
            systolic=st.number_input("Systolic BP (mmHg)",0,400,120)
            diastolic=st.number_input("Diastolic BP (mmHg)",0,300,80)
        with v4:
            o2_level=st.number_input("SpO₂ (%)",0,100,98)
            hemoglobin=st.number_input("Hemoglobin (g/dL)",0.0,30.0,12.5,step=0.1)
        live_bmi=calculate_bmi(weight,height)
        cat,cls=bmi_category(live_bmi)
        badge_map={"ok":"badge-green","warn":"badge-yellow","danger":"badge-red","muted":"badge-blue"}
        bc=badge_map.get(cls,"badge-blue")
        st.markdown(f"""
        <div style="background:#f0f4fb;border:1.5px solid #dde3f0;border-radius:10px;
            padding:.75rem 1.25rem;display:flex;align-items:center;gap:12px;margin:.5rem 0 1rem;">
            <span style="color:#6b7a99;font-size:.85rem;font-weight:600;">Calculated BMI:</span>
            <span style="font-size:1.1rem;font-weight:700;color:#1a6fd4;">{live_bmi or '—'}</span>
            <span class="badge {bc}">{cat}</span>
        </div>""",unsafe_allow_html=True)

        st.markdown("<hr style='border-color:#dde3f0;margin:0 0 1.25rem;'>",unsafe_allow_html=True)

        # ── Section 3: Health Assessment ──────────
        st.markdown('<div class="section-title"><span class="icon">🏥</span> Health Assessment</div>',unsafe_allow_html=True)
        ha1,ha2=st.columns(2)
        with ha1:
            vision=st.radio("Vision",["Clear","Blurry","Needs Glasses"],horizontal=True)
            breathing=st.radio("Breathing",["Normal","Slight Difficulty","Labored"],horizontal=True)
            hearing=st.radio("Hearing",["Normal","Mild Loss","Significant Loss"],horizontal=True)
        with ha2:
            skin_condition=st.radio("Skin Condition",["Clear","Mild Issues","Severe Issues"],horizontal=True)
            oral_health=st.radio("Oral Health",["No issues","Bleeding gums","Bad breath","Frequent mouth ulcers","Tooth pain or sensitivity"],horizontal=True)
            cataract=st.radio("Cataract",["No","Yes"],horizontal=True)

        st.markdown("<hr style='border-color:#dde3f0;margin:.75rem 0 1.25rem;'>",unsafe_allow_html=True)

        # ── Section 4: Additional ─────────────────
        st.markdown('<div class="section-title"><span class="icon">📝</span> Additional Information</div>',unsafe_allow_html=True)
        ad1,ad2,ad3=st.columns(3)
        with ad1: urine_color=st.selectbox("Urine Color",["Pale yellow","Clear","Dark yellow","Brownish/red (seek medical attention)"])
        with ad2: hair_loss=st.selectbox("Hair Loss",["No","Yes, mild hair loss","Yes, moderate hair loss","Yes, severe hair loss"])
        with ad3: nail_changes=st.radio("Nail Abnormalities",["No","Yes, white spots","Yes, yellowing","Yes, dark streaks"],horizontal=True)
        disabilities=st.text_area("Disabilities / Additional Notes","",height=80)
        uploaded_pdf=st.file_uploader("Attach additional PDF (optional – will be merged)",type=["pdf"])

        st.markdown("<div style='height:.75rem'></div>",unsafe_allow_html=True)
        submitted=st.form_submit_button("🚀  Generate Medical Report",type="primary",use_container_width=True)

    # ── Post-submit ────────────────────────────
    if submitted:
        data={
            "patient_name":patient_name,"patient_age":patient_age,"patient_gender":patient_gender,
            "patient_phone":patient_phone,"email":email,"patient_referee":patient_referee,
            "collection_date":collection_date.strftime("%Y-%m-%d"),"report_date":report_date.strftime("%Y-%m-%d"),
            "report_ID":report_ID,"patient_ID":patient_ID,
            "weight":weight,"height":height,"bmi":calculate_bmi(weight,height),
            "temperature":temperature,"pulse_rate":pulse_rate,
            "systolic_blood_pressure":systolic,"diastolic_blood_pressure":diastolic,
            "o2_level":o2_level,"hemoglobin_level":hemoglobin,
            "vision":vision,"breathing":breathing,"hearing":hearing,
            "skin_condition":skin_condition,"oral_health":oral_health,
            "urine_color":urine_color,"hair_loss":hair_loss,"nail_changes":nail_changes,
            "cataract":cataract,"disabilities":disabilities,
        }
        prog=st.progress(0,"Starting…")
        try:
            prog.progress(20,"Saving to database…")
            try: save_response(data)
            except Exception as e: st.warning(f"DB save failed: {e}")
            prog.progress(50,"Generating PDF…")
            out=create_medical_report(data)
            prog.progress(75,"Finalising…")
            if uploaded_pdf:
                merger=PdfMerger(); merger.append(out)
                up_path="generated_files/uploaded.pdf"
                os.makedirs("generated_files",exist_ok=True)
                with open(up_path,"wb") as f: f.write(uploaded_pdf.getbuffer())
                merger.append(up_path)
                merged="generated_files/merged_report.pdf"
                merger.write(merged); merger.close(); out=merged
            prog.progress(88,"Syncing…")
            if sheet:
                try: save_to_google_sheets(data)
                except: pass
            if email and SMTP_USER:
                try: send_email(email,"Medical Diagnostic Report","Please find your report attached.",out)
                except: pass
            prog.progress(100,"Done!")
            time.sleep(0.3); prog.empty()
            st.session_state.report_generated=True
            st.session_state.final_pdf=out
            st.session_state.report_data=data
            st.balloons(); st.rerun()
        except Exception as e:
            prog.empty(); st.error(f"❌ Error: {e}")

# ── ROUTER ──
if "authenticated" not in st.session_state: st.session_state.authenticated=False
if "current_page" not in st.session_state: st.session_state.current_page="login"

inject_css(); init_db()

page=st.session_state.current_page
if page=="login": login_page()
elif page=="generate_report":
    if not st.session_state.authenticated:
        st.session_state.current_page="login"; st.rerun()
    else: report_generation_page()
else:
    st.session_state.current_page="login"; st.rerun()