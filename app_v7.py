# app.py
import os
import streamlit as st
import smtplib
from email.message import EmailMessage
from PyPDF2 import PdfMerger
import psycopg2
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from dotenv import load_dotenv
from datetime import datetime
from fpdf import FPDF

# -------------------------
# Load environment variables
# -------------------------
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")          # e.g. 10minutemail24@gmail.com
SMTP_PASS = os.getenv("SMTP_PASS")          # app password or real password (use app password)

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "StreamlitData")

# -------------------------
# Google Sheets setup
# -------------------------
sheet = None
try:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open(GOOGLE_SHEET_NAME).sheet1
except Exception as e:
    # We'll show an error in the UI rather than crash
    sheet = None
    sheet_init_error = str(e)
else:
    sheet_init_error = None

# -------------------------
# Helpers: DB connection
# -------------------------
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except psycopg2.OperationalError as e:
        raise RuntimeError(f"Error connecting to DB: {e}")


# -------------------------
# Utility functions
# -------------------------
def parse_date(d):
    """Try to parse date string (YYYY-MM-DD or common formats). Return date string or None."""
    if not d:
        return None
    if isinstance(d, datetime):
        return d.date()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(d, fmt).date()
        except Exception:
            pass
    # Try ISO parse fallback
    try:
        return datetime.fromisoformat(d).date()
    except Exception:
        return None


def calculate_bmi(weight, height):
    try:
        weight = float(weight)
        height = float(height)
        if height == 0:
            return None
        height_m = height / 100.0
        return round(weight / (height_m ** 2), 1)
    except Exception:
        return None


def comments_to_paragraph(comments):
    if not comments:
        return "No significant abnormalities detected."
    if len(comments) == 1:
        return comments[0]
    if len(comments) == 2:
        return comments[0] + " and " + comments[1]
    return ", ".join(comments[:-1]) + ", and " + comments[-1]


def analyze_numerical_vitals(data):
    comments = []
    # BMI
    bmi = data.get('bmi')
    if bmi is not None:
        try:
            bmi = float(bmi)
            if bmi < 18.5:
                comments.append("The patient is underweight")
            elif 25 <= bmi <= 29.9:
                comments.append("The patient is overweight")
            elif bmi >= 30:
                comments.append("The patient is obese")
        except Exception:
            pass

    # Blood Pressure
    bp = data.get('blood_pressure')
    if bp and isinstance(bp, str) and '/' in bp:
        try:
            systolic, diastolic = map(int, bp.split('/'))
            if systolic < 90 or diastolic < 60:
                comments.append("The patient has low blood pressure")
            elif systolic > 120 or diastolic > 80:
                comments.append("The patient has high blood pressure")
        except Exception:
            comments.append("Invalid blood pressure reading")

    # Temperature (assume °F)
    temperature = data.get('temperature')
    try:
        if temperature is not None:
            temperature = float(temperature)
            if temperature < 97.8:
                comments.append("The patient has a low body temperature")
            elif temperature > 99.1:
                comments.append("The patient has a fever")
    except Exception:
        comments.append("Invalid temperature reading")

    # SpO2
    spo2 = data.get('o2_level')
    try:
        if spo2 is not None:
            spo2_val = float(str(spo2).replace('%', '').strip())
            if spo2_val < 94:
                comments.append("The patient has low SpO2 (possible hypoxemia)")
    except Exception:
        comments.append("Invalid SpO2 reading")

    # Pulse
    pulse = data.get('pulse_rate')
    try:
        if pulse is not None:
            pulse_val = float(pulse)
            if pulse_val < 60:
                comments.append("The patient has bradycardia (low pulse rate)")
            elif pulse_val > 100:
                comments.append("The patient has tachycardia (high pulse rate)")
    except Exception:
        comments.append("Invalid pulse rate reading")

    return comments


def analyze_subjective_answers(data):
    comments = []
    hair_loss = data.get('hair_loss')
    if hair_loss == "Yes, severe hair loss":
        comments.append("The doctor needs to urgently look at the patient's hair condition.")
    elif hair_loss in ["Yes, mild hair loss", "Yes, moderate hair loss"]:
        comments.append("Deeper inspection is required for the patient's hair condition.")

    nail_changes = data.get('nail_changes')
    if nail_changes == "Yes, dark streaks":
        comments.append("The doctor needs to urgently look at the patient's nail condition.")
    elif nail_changes in ["Yes, white spots", "Yes, yellowing"]:
        comments.append("Deeper inspection is required for the patient's nail condition.")

    urine_color = data.get('urine_color')
    if urine_color == "Brownish/red (seek medical attention)":
        comments.append("The doctor needs to urgently look at the patient's urinary condition.")
    elif urine_color == "Dark yellow":
        comments.append("Urinary condition may depict an underlying symptom.")

    oral_health = data.get('oral_health')
    if oral_health in ["Bleeding gums", "Frequent mouth ulcers"]:
        comments.append("The doctor needs to urgently look at the patient's mouth condition.")
    elif oral_health in ["Bad breath", "Tooth pain or sensitivity"]:
        comments.append("Mouth condition may depict an underlying symptom.")

    return comments


# -------------------------
# PDF generation (kept your original layout but safer fetching)
# -------------------------
class PDF(FPDF):
    def header(self):
        self.set_draw_color(0, 0, 0)
        self.rect(5, 5, 200, 287)
        logo_path = "assets/kgp_logo.png"
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 8, 25)
        self.set_font('Times', 'B', 16)
        self.set_xy(0, 10)
        self.cell(0, 10, "Indian Institute of Technology Kharagpur", 0, 1, 'C')
        self.set_font('Times', 'B', 14)
        self.cell(0, 10, "Solar-Powered Mobile Health Measurement Device", 0, 1, 'C')
        self.ln(8)

    def footer(self):
        self.set_y(-20)
        self.set_font('Times', 'I', 10)
        self.cell(0, 10, '~ End of Report ~', 0, 0, 'C')

    def patient_info(self, left_info, right_info):
        self.set_font('Times', '', 10)
        initial_y = self.get_y()
        self.multi_cell(95, 7, "\n".join([f"{k}: {v}" for k, v in left_info.items()]), 0, 'L')
        self.set_y(initial_y)
        self.set_x(105)
        self.multi_cell(95, 7, "\n".join([f"{k}: {v}" for k, v in right_info.items()]), 0, 'L')
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def add_dates(self, left_date_info, right_date_info):
        self.set_font('Times', '', 10)
        initial_y = self.get_y()
        self.multi_cell(95, 7, "\n".join([f"{k}: {v}" for k, v in left_date_info.items()]), 0, 'L')
        self.set_y(initial_y)
        self.set_x(105)
        self.multi_cell(95, 7, "\n".join([f"{k}: {v}" for k, v in right_date_info.items()]), 0, 'L')
        self.ln(6)
        self.line(10, self.get_y(), 200, self.get_y())

    def chapter_title(self, title):
        self.set_font('Times', 'B', 12)
        self.cell(0, 8, title, 0, 1, 'L')
        self.ln(4)

    def test_table_1(self, test_info):
        self.set_font('Times', 'B', 10)
        col_widths = [60, 40, 50, 40]
        headers = ['VITALS', 'RESULT', 'REF. RANGE', 'UNIT']
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 7, header, 1, 0, 'C')
        self.ln()
        self.set_font('Times', '', 9)
        for test in test_info:
            self.cell(col_widths[0], 7, test['description'], 1)
            self.cell(col_widths[1], 7, str(test.get('result', '')), 1)
            self.cell(col_widths[2], 7, test.get('range', ''), 1)
            self.cell(col_widths[3], 7, test.get('unit', ''), 1)
            self.ln()

    def test_table_2(self, test_info):
        self.set_font('Times', 'B', 10)
        col_widths = [20, 120, 50]
        headers = ['Sl.No', 'QUESTIONS', 'RESPONSE']
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 7, header, 1, 0, 'C')
        self.ln()
        self.set_font('Times', '', 9)
        for i, test in enumerate(test_info):
            self.cell(col_widths[0], 7, str(i + 1) + '.', 1, align='C')
            self.cell(col_widths[1], 7, test.get('description', ''), 1)
            self.cell(col_widths[2], 7, str(test.get('result', '')), 1)
            self.ln()

    def add_comments(self, comments):
        self.set_font('Times', 'B', 12)
        self.cell(0, 10, 'Comments:', 0, 1)
        self.set_font('Times', '', 11)
        self.multi_cell(0, 6, comments)


def create_medical_report(data):
    os.makedirs("generated_files", exist_ok=True)
    pdf = PDF()
    pdf.add_page()

    # Dates as strings for display
    left_dates = {'Collection Date': data.get('collection_date') or ""}
    right_dates = {'Report Date': data.get('report_date') or ""}
    pdf.add_dates(left_dates, right_dates)

    # Patient info
    pdf.patient_info(
        {
            'Name': data.get('patient_name', ''),
            'Age/Gender': data.get('patient_age_gender', ''),
            'Referred By': data.get('patient_referee', '')
        },
        {
            'Contact': data.get('patient_phone', ''),
            'Patient ID': str(data.get('patient_ID', '')),
            'Report ID': str(data.get('report_ID', ''))
        }
    )

    # Vitals
    pdf.chapter_title('Body Vitals')
    bmi = data.get('bmi') or calculate_bmi(data.get('weight'), data.get('height'))
    data['bmi'] = bmi
    test_info_vitals = [
        {'description': 'Weight', 'result': f"{data.get('weight', '')} kg", 'range': '-', 'unit': 'kg'},
        {'description': 'Height', 'result': f"{data.get('height', '')} cm", 'range': '-', 'unit': 'cm'},
        {'description': 'BMI', 'result': bmi if bmi is not None else "", 'range': '18.5-24.9', 'unit': 'kg/m²'},
        {'description': 'SpO2', 'result': data.get('o2_level', ''), 'range': '94-100%', 'unit': '%'},
        {'description': 'Temperature', 'result': f"{data.get('temperature', '')}°F", 'range': '97.8-99.1', 'unit': '°F'},
        {'description': 'Pulse Rate', 'result': f"{data.get('pulse_rate', '')} bpm", 'range': '60-100', 'unit': 'bpm'},
        {'description': 'BP', 'result': data.get('blood_pressure', ''), 'range': '90/60-140/90', 'unit': 'mmHg'}
    ]
    pdf.test_table_1(test_info_vitals)

    # General Questions
    pdf.chapter_title('General Health Questions')
    test_info_general = [
        {'description': "Can you see clearly without glasses?", 'result': data.get('vision', '')},
        {'description': "Do you experience difficulty in breathing?", 'result': data.get('breathing', '')},
        {'description': "Do you have any difficulty in hearing?", 'result': data.get('hearing', '')},
        {'description': "Do you have any visible skin conditions?", 'result': data.get('skin_condition', '')},
        {'description': "Do you experience any mouth conditions?", 'result': data.get('oral_health', '')},
        {'description': "What is your usual urine colour?", 'result': data.get('urine_color', '')},
        {'description': "Have you noticed significant hair loss recently?", 'result': data.get('hair_loss', '')},
        {'description': "Have you noticed any unusual changes in your nail colour?", 'result': data.get('nail_changes', '')},
        {'description': "Have you been diagnosed with or noticed signs of cataract?", 'result': data.get('cataract', '')},
        {'description': "Do you have any physical disabilities?", 'result': data.get('disabilities', '')}
    ]
    pdf.test_table_2(test_info_general)

    # comments section
    numerical_comments = analyze_numerical_vitals(data)
    subjective_comments = analyze_subjective_answers(data)
    all_comments = numerical_comments + subjective_comments
    if all_comments:
        comments_paragraph = ". ".join(all_comments) + "."
        pdf.add_comments(comments_paragraph)

    output_file = "generated_files/medical_report.pdf"
    pdf.output(output_file)
    return output_file


# -------------------------
# Save response (robust)
# -------------------------
def save_response(data):
    """
    Inserts into responses. Builds column list dynamically to avoid mismatches.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # columns to insert (must match the table created in init_db)
        cols = [
            "collection_date", "report_date", "report_id", "patient_id", "patient_name",
            "patient_age_gender", "patient_referee", "patient_phone", "weight", "height",
            "bmi", "pulse_rate", "blood_pressure", "o2_level", "temperature", "vision",
            "breathing", "hearing", "skin_condition", "oral_health", "urine_color",
            "hair_loss", "nail_changes", "cataract", "disabilities"
        ]

        # Prepare values (parse dates)
        vals = []
        for c in cols:
            if c in ("collection_date", "report_date"):
                parsed = parse_date(data.get(c))
                vals.append(parsed)
            else:
                vals.append(data.get(c))

        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"INSERT INTO responses ({', '.join(cols)}) VALUES ({placeholders})"
        cur.execute(sql, tuple(vals))
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# -------------------------
# Auth & DB init
# -------------------------
def authenticate(username, password):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username = %s", (username,))
        stored = cur.fetchone()
        conn.close()
        return stored and stored[0] == password
    except Exception:
        return False


def register_user(username, password):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cur.fetchone() is not None:
            return False, "Username already exists"
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        conn.close()
        return True, "Registration successful!"
    except Exception as e:
        return False, f"Error during registration: {str(e)}"


def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id SERIAL PRIMARY KEY,
                collection_date DATE,
                report_date DATE,
                report_id INTEGER,
                patient_id INTEGER,
                patient_name VARCHAR(100),
                patient_age_gender VARCHAR(50),
                patient_referee VARCHAR(100),
                patient_phone VARCHAR(20),
                weight NUMERIC(7,2),
                height NUMERIC(7,2),
                bmi NUMERIC(7,2),
                pulse_rate INTEGER,
                blood_pressure VARCHAR(20),
                o2_level VARCHAR(10),
                temperature NUMERIC(7,2),
                vision VARCHAR(50),
                breathing TEXT,
                hearing TEXT,
                skin_condition TEXT,
                oral_health TEXT,
                urine_color TEXT,
                hair_loss TEXT,
                nail_changes TEXT,
                cataract TEXT,
                disabilities TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"DB init error: {e}")


# -------------------------
# UI: login/register
# -------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"

def login_page():
    st.markdown("<style>/* small UI reset to avoid huge CSS injection issues */</style>", unsafe_allow_html=True)
    st.header("Welcome — Sign in")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sign In"):
            if authenticate(username, password):
                st.session_state.authenticated = True
                st.session_state.current_page = "generate_report"
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")
    with col2:
        if st.button("Register"):
            st.session_state.current_page = "register"
            st.experimental_rerun()

def register_page():
    st.header("Create Account")
    new_username = st.text_input("Username", key="reg_username")
    new_password = st.text_input("Password", type="password", key="reg_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
    if st.button("Create Account"):
        if not new_username or not new_password:
            st.error("Username and password are required")
        elif new_password != confirm_password:
            st.error("Passwords do not match")
        else:
            success, message = register_user(new_username, new_password)
            if success:
                st.success(message)
                st.session_state.current_page = "login"
                st.experimental_rerun()
            else:
                st.error(message)


# -------------------------
# Report generation page
# -------------------------
def report_generation_page():
    st.title("Medical Diagnostic Report Generator")

    # Show Google Sheets init error if any
    if sheet_init_error:
        st.warning(f"Google Sheets init failed: {sheet_init_error}. Sheet features will be disabled.")

    final_pdf_path = None
    with st.form(key="input_form"):
        st.write("Enter patient details:")
        data = {
            "collection_date": st.text_input("Collection Date (YYYY-MM-DD)", value="2025-04-15"),
            "report_date": st.text_input("Report Date (YYYY-MM-DD)", value="2025-04-15"),
            "report_ID": int(st.number_input("Report ID", min_value=0, value=1001)),
            "patient_ID": int(st.number_input("Patient ID", min_value=0, value=5001)),
            "patient_name": st.text_input("Patient Name", value="John Doe"),
            "patient_age_gender": st.text_input("Patient Age/Gender", value="30/M"),
            "patient_referee": st.text_input("Referred By", value="Dr. Smith"),
            "patient_phone": st.text_input("Phone Number", value="9876543210"),
            "email": st.text_input("Email (optional)", value="", placeholder="Enter email to send the report"),
            "weight": st.number_input("Weight (kg)", min_value=0.0, value=0.0, format="%.2f"),
            "height": st.number_input("Height (cm)", min_value=0.0, value=0.0, format="%.2f"),
            "pulse_rate": int(st.number_input("Pulse Rate (bpm)", min_value=0, value=72)),
            "blood_pressure": st.text_input("Blood Pressure (mmHg)", value="120/80"),
            "o2_level": st.text_input("SpO2 (%)", value="98"),
            "temperature": st.number_input("Temperature (°F)", min_value=80.0, value=98.6, format="%.1f"),
            "vision": st.radio("Can you see clearly without glasses?", ["Yes", "No", "Not Sure"], index=0),
            "breathing": st.radio("Do you experience difficulty in breathing?",
                                  ["No difficulty", "Often, even at rest", "Occasionally, during physical activity",
                                   "Only during certain conditions"], index=0),
            "hearing": st.radio("Do you have any difficulty in hearing?",
                                ["No", "Yes, in one ear", "Yes, in both ears", "Not Sure"], index=0),
            "skin_condition": st.radio("Do you have any visible skin conditions?",
                                       ["Not Sure", "Yes, mild", "Yes, moderate", "Yes, severe"], index=0),
            "oral_health": st.radio("Do you experience any mouth conditions?",
                                    ["No issues", "Bleeding gums", "Bad breath", "Frequent mouth ulcers",
                                     "Tooth pain or sensitivity"], index=0),
            "urine_color": st.radio("What is your usual urine colour?",
                                    ["Clear", "Pale yellow", "Dark yellow", "Brownish/red (seek medical attention)"],
                                    index=0),
            "hair_loss": st.radio("Have you noticed significant hair loss recently?",
                                  ["No", "Yes, mild hair loss", "Yes, moderate hair loss", "Yes, severe hair loss"],
                                  index=0),
            "nail_changes": st.radio("Have you noticed any unusual changes in your nail colour?",
                                     ["No", "Yes, white spots", "Yes, yellowing", "Yes, dark streaks"], index=0),
            "cataract": st.radio("Have you been diagnosed with or noticed signs of cataract?",
                                 ["No", "Yes, diagnosed by a doctor", "Yes, not diagnosed yet"], index=0),
            "disabilities": st.radio("Do you have any physical disabilities?",
                                     ["No", "Yes, partial mobility issues", "Yes, require walking aids",
                                      "Yes, fully dependent on assistance"], index=0)
        }
        uploaded_pdf = st.file_uploader("Upload a PDF to merge with the report (optional)", type=["pdf"])
        submit = st.form_submit_button("Generate PDF")

    if submit:
        try:
            # Normalize dates for DB but keep string for display
            data["collection_date"] = data.get("collection_date")
            data["report_date"] = data.get("report_date")

            # Calculate BMI and attach
            data["bmi"] = calculate_bmi(data.get("weight"), data.get("height"))

            # Save to DB
            try:
                save_response(data)
            except Exception as e:
                st.error(f"Failed to save to database: {e}")

            # Generate PDF
            output_file = create_medical_report(data)
            st.success("PDF generated successfully!")

            # Merge uploaded PDF if present
            if uploaded_pdf is not None:
                merger = PdfMerger()
                merger.append(output_file)
                uploaded_path = "generated_files/uploaded.pdf"
                with open(uploaded_path, "wb") as f:
                    f.write(uploaded_pdf.read())
                merger.append(uploaded_path)
                merged_pdf_path = "generated_files/merged_report.pdf"
                merger.write(merged_pdf_path)
                merger.close()
                st.session_state['final_pdf'] = merged_pdf_path
                final_pdf_path = merged_pdf_path
            else:
                st.session_state['final_pdf'] = output_file
                final_pdf_path = output_file

            # Optionally append a row to Google Sheet
            if sheet is not None:
                try:
                    row = [
                        str(data.get("collection_date") or ""),
                        str(data.get("report_date") or ""),
                        data.get("report_ID"),
                        data.get("patient_ID"),
                        data.get("patient_name"),
                        data.get("patient_age_gender"),
                        data.get("patient_referee"),
                        data.get("patient_phone"),
                        data.get("weight"),
                        data.get("height"),
                        data.get("bmi"),
                        data.get("pulse_rate"),
                        data.get("blood_pressure"),
                        data.get("o2_level"),
                        data.get("temperature"),
                    ]
                    sheet.append_row(row)
                except Exception as e:
                    st.warning(f"Could not write to Google Sheet: {e}")

            # Send email if provided
            if data.get("email") and final_pdf_path:
                if not SMTP_USER or not SMTP_PASS:
                    st.warning("SMTP credentials not set in environment; skipped sending email.")
                else:
                    try:
                        msg = EmailMessage()
                        msg["Subject"] = "Medical Diagnostic Report"
                        msg["From"] = SMTP_USER
                        msg["To"] = data["email"]
                        msg.set_content("Attached is your medical diagnostic report.")
                        with open(final_pdf_path, "rb") as pdf:
                            msg.add_attachment(pdf.read(), maintype="application", subtype="pdf", filename="medical_report.pdf")

                        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                            server.starttls()
                            server.login(SMTP_USER, SMTP_PASS)
                            server.send_message(msg)
                        st.success(f"Report sent to {data['email']}")
                    except Exception as e:
                        st.error(f"Error sending email: {e}")

        except Exception as e:
            st.error(f"Error generating report: {e}")
            st.session_state['final_pdf'] = None

    # Download button
    if st.session_state.get('final_pdf'):
        with open(st.session_state['final_pdf'], "rb") as pdf_file:
            st.download_button(
                label="Download PDF",
                data=pdf_file,
                file_name="medical_report.pdf",
                mime="application/pdf"
            )

    if st.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.current_page = "login"
        # clear final pdf
        st.session_state.pop('final_pdf', None)
        st.experimental_rerun()


# -------------------------
# App init & routing
# -------------------------
init_db()

if st.session_state.current_page == "login":
    login_page()
elif st.session_state.current_page == "register":
    register_page()
elif st.session_state.current_page == "generate_report":
    if not st.session_state.authenticated:
        st.session_state.current_page = "login"
        st.experimental_rerun()
    report_generation_page()
else:
    st.write("Unknown page state. Resetting.")
    st.session_state.current_page = "login"
    st.experimental_rerun()
