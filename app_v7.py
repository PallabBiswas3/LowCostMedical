import streamlit as st
import smtplib
from email.message import EmailMessage
from PyPDF2 import PdfMerger
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
import os
from datetime import datetime

# Set page config first
st.set_page_config(
    page_title="Medical Report System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    css_path = Path(_file_).parent / "static" / "styles.css"
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Initialize the app with custom styles
load_css()

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    """Create a database connection using environment variables"""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to database: {e}")
        print("Please check your .env file and ensure PostgreSQL is running.")
        raise

def authenticate(username, password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username = %s", (username,))
    stored_password = cur.fetchone()
    conn.close()
    return stored_password and stored_password[0] == password

def calculate_bmi(weight, height):
    if not weight or not height or height == 0:
        return "NA"
    try:
        height_m = height / 100
        return f"{(weight / (height_m ** 2)):.1f}"
    except (TypeError, ValueError):
        return "NA"

def comments_to_paragraph(comments):
    if not comments:
        return "No significant abnormalities detected."
    if len(comments) == 1:
        return comments[0]
    elif len(comments) == 2:
        return comments[0] + " and " + comments[1]
    else:
        return ", ".join(comments[:-1]) + ", and " + comments[-1]

def analyze_numerical_vitals(data):
    comments = []

    # BMI
    bmi = data.get('bmi')
    if bmi and bmi != "NA":
        try:
            bmi = float(bmi)
            if bmi < 18.5:
                comments.append("The patient is underweight")
            elif 18.5 <= bmi <= 24.9:
                pass  # Normal, no comment
            elif 25 <= bmi <= 29.9:
                comments.append("The patient is overweight")
            else:
                comments.append("The patient is obese")
        except (ValueError, TypeError):
            pass

    # Blood Pressure
    bp = data.get('blood_pressure')
    if bp and '/' in bp:
        try:
            systolic, diastolic = map(int, bp.split('/'))
            if systolic < 90 or diastolic < 60:
                comments.append("the patient has low blood pressure")
            elif 90 <= systolic <= 120 and 60 <= diastolic <= 80:
                pass  # Normal, no comment
            elif systolic > 120 or diastolic > 80:
                comments.append("the patient has high blood pressure")
        except (ValueError, TypeError):
            comments.append("invalid blood pressure reading")

    # Temperature
    temperature = data.get('temperature')
    if temperature:
        try:
            temperature = float(temperature)
            if temperature < 97.8:
                comments.append("the patient has a low body temperature")
            elif 97.8 <= temperature <= 99.1:
                pass  # Normal, no comment
            else:
                comments.append("the patient has a fever")
        except (ValueError, TypeError):
            comments.append("invalid temperature reading")

    # SpO2
    spo2 = data.get('o2_level')
    if spo2:
        try:
            spo2_val = float(str(spo2).replace('%', '').strip())
            if spo2_val < 94:
                comments.append("the patient has low SpO2 (possible hypoxemia)")
            elif 94 <= spo2_val <= 100:
                pass  # Normal, no comment
            else:
                comments.append("the patient has abnormally high SpO2")
        except (ValueError, TypeError):
            comments.append("invalid SpO2 reading")

    # Pulse Rate
    pulse = data.get('pulse_rate')
    if pulse:
        try:
            pulse_val = float(pulse)
            if pulse_val < 60:
                comments.append("the patient has bradycardia (low pulse rate)")
            elif 60 <= pulse_val <= 100:
                pass  # Normal, no comment
            else:
                comments.append("the patient has tachycardia (high pulse rate)")
        except (ValueError, TypeError):
            comments.append("invalid pulse rate reading")

    return comments

def analyze_subjective_answers(data):
    comments = []

    # Hair loss
    hair_loss = data.get('hair_loss')
    if hair_loss == "Yes, severe hair loss":
        comments.append("The doctor needs to urgently look at the patient's hair condition.")
    elif hair_loss in ["Yes, mild hair loss", "Yes, moderate hair loss"]:
        comments.append("Deeper inspection is required for the patient's hair condition.")

    # Nail changes
    nail_changes = data.get('nail_changes')
    if nail_changes == "Yes, dark streaks":
        comments.append("The doctor needs to urgently look at the patient's nail condition.")
    elif nail_changes in ["Yes, white spots", "Yes, yellowing"]:
        comments.append("Deeper inspection is required for the patient's nail condition.")

    # Urine color
    urine_color = data.get('urine_color')
    if urine_color == "Brownish/red (seek medical attention)":
        comments.append("The doctor needs to urgently look at the patient's urinary condition.")
    elif urine_color == "Dark yellow":
        comments.append("Urinary condition may depict an underlying symptom.")

    # Oral health
    oral_health = data.get('oral_health')
    if oral_health in ["Bleeding gums", "Frequent mouth ulcers"]:
        comments.append("The doctor needs to urgently look at the patient's mouth condition.")
    elif oral_health in ["Bad breath", "Tooth pain or sensitivity"]:
        comments.append("Mouth condition may depict an underlying symptom.")

    return comments

def create_medical_report(data):
    from fpdf import FPDF
    import os

    class PDF(FPDF):
        def header(self):
            self.set_draw_color(0, 0, 0)
            self.rect(5, 5, 200, 287)
            self.image('assets/kgp_logo.png', 10, 8, 25)
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
                self.cell(col_widths[1], 7, str(test['result']), 1)
                self.cell(col_widths[2], 7, test['range'], 1)
                self.cell(col_widths[3], 7, test['unit'], 1)
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
                self.cell(col_widths[1], 7, test['description'], 1)
                self.cell(col_widths[2], 7, test['result'], 1)
                self.ln()

        def add_comments(self, comments):
            self.set_font('Times', 'B', 12)
            self.cell(0, 10, 'Comments:', 0, 1)
            self.set_font('Times', '', 11)
            self.multi_cell(0, 6, comments)

    os.makedirs("generated_files", exist_ok=True)
    pdf = PDF()
    pdf.add_page()

    # Add dates
    pdf.add_dates(
        {'Collection Date': data['collection_date']},
        {'Report Date': data['report_date']}
    )

    # Patient info
    pdf.patient_info(
        {
            'Name': data['patient_name'],
            'Age/Gender': data['patient_age_gender'],
            'Referred By': data['patient_referee']
        },
        {
            'Contact': data['patient_phone'],
            'Patient ID': str(data['patient_ID']),
            'Report ID': data['report_ID']
        }
    )

    # Vitals
    pdf.chapter_title('Body Vitals')
    bmi = calculate_bmi(data.get('weight'), data.get('height'))
    data['bmi'] = bmi  # analysis
    test_info_vitals = [
        {'description': 'Weight', 'result': f"{data.get('weight', '')} kg", 'range': '-', 'unit': 'kg'},
        {'description': 'Height', 'result': f"{data.get('height', '')} cm", 'range': '-', 'unit': 'cm'},
        {'description': 'BMI', 'result': bmi, 'range': '18.5-24.9', 'unit': 'kg/m²'},
        {'description': 'SpO2', 'result': data['o2_level'], 'range': '94-100%', 'unit': '%'},
        {'description': 'Temperature', 'result': f"{data['temperature']}°F", 'range': '97.8-99.1', 'unit': '°F'},
        {'description': 'Pulse Rate', 'result': f"{data['pulse_rate']} bpm", 'range': '60-100', 'unit': 'bpm'},
        {'description': 'BP', 'result': data['blood_pressure'], 'range': '90/60-140/90', 'unit': 'mmHg'}
    ]
    pdf.test_table_1(test_info_vitals)

    # General Questions
    pdf.chapter_title('General Health Questions')
    test_info_general = [
        {'description': "Can you see clearly without glasses?", 'result': data['vision']},
        {'description': "Do you experience difficulty in breathing?", 'result': data['breathing']},
        {'description': "Do you have any difficulty in hearing?", 'result': data['hearing']},
        {'description': "Do you have any visible skin conditions?", 'result': data['skin_condition']},
        {'description': "Do you experience any mouth conditions?", 'result': data['oral_health']},
        {'description': "What is your usual urine colour?", 'result': data['urine_color']},
        {'description': "Have you noticed significant hair loss recently?", 'result': data['hair_loss']},
        {'description': "Have you noticed any unusual changes in your nail colour?", 'result': data['nail_changes']},
        {'description': "Have you been diagnosed with or noticed signs of cataract?", 'result': data['cataract']},
        {'description': "Do you have any physical disabilities?", 'result': data['disabilities']}
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

# the below function's inputs are not exactly correct, need toto correct them
# also need to update database columns accordingly
# need to create .env file for secret keys and privacy
def save_response(data):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO responses (
            collection_date, report_date, report_id, patient_id, patient_name,
            patient_age_gender, patient_referee, patient_phone, weight, height, BMI,
            pulse_rate, blood_pressure, o2_level, temperature, vision, breathing, hearing, 
            skin_condition, oral_health, urine_color, hair_loss, nail_changes, 
            cataract, disabilities
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        data['collection_date'], data['report_date'], data['report_ID'],
        data['patient_ID'], data['patient_name'], data['patient_age_gender'],
        data['patient_referee'], data['patient_phone'], data['weight'], data['height'], data['bmi'],
        data['pulse_rate'], data['blood_pressure'], data['o2_level'], data['temperature'],
        data['vision'], data['breathing'], data['hearing'], data['skin_condition'],
        data['oral_health'], data['urine_color'], data['hair_loss'],
        data['nail_changes'], data['cataract'], data['disabilities']
    ))
    conn.commit()
    conn.close()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"

def register_user(username, password):
    """Register a new user in the database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user already exists
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cur.fetchone() is not None:
            return False, "Username already exists"
            
        # Insert new user
        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, password)
        )
        conn.commit()
        return True, "Registration successful!"
    except Exception as e:
        return False, f"Error during registration: {str(e)}"
    finally:
        if 'conn' in locals():
            conn.close()

def login_page():
    st.markdown("""
    <div class="auth-container">
        <h1 class="text-center">👨‍⚕ Medical Report System</h1>
        <p class="text-center mb-3">Please login or register to continue</p>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            st.markdown("<h2 class='text-center'>🔑 Login</h2>", unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_button = st.form_submit_button("Login", type="primary", use_container_width=True)
            
            if login_button:
                if not username or not password:
                    st.error("Please fill in all fields")
                elif authenticate(username, password):
                    st.session_state.authenticated = True
                    st.session_state.current_page = "report_generation"
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
    
    with tab2:
        with st.form("register_form"):
            st.markdown("<h2 class='text-center'>📝 Register</h2>", unsafe_allow_html=True)
            new_username = st.text_input("Choose a username", placeholder="Enter a username")
            new_password = st.text_input("Choose a password", type="password", 
                                       placeholder="Create a strong password")
            confirm_password = st.text_input("Confirm password", type="password", 
                                           placeholder="Re-enter your password")
            register_button = st.form_submit_button("Create Account", type="primary", 
                                                 use_container_width=True)
            
            if register_button:
                if not new_username or not new_password or not confirm_password:
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("❌ Passwords do not match")
                else:
                    if register_user(new_username, new_password):
                        st.success("✅ Registration successful! Please login.")
                    else:
                        st.error("❌ Username already exists")
    
    st.markdown("</div>", unsafe_allow_html=True)

def report_generation_page():
    # Add a nice header with user info
    if 'username' in st.session_state:
        st.sidebar.markdown(f"### 👤 {st.session_state.username}")
        if st.sidebar.button("Logout", type="secondary", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_page = "login"
            st.rerun()
    
    st.markdown("""
    <div class="stCard">
        <h1 class="text-center">🏥 Medical Report Generator</h1>
        <p class="text-center">Fill in the patient details to generate a comprehensive medical report</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("patient_info"):
        with st.container():
            st.markdown("<h2>📋 Patient Information</h2>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name", placeholder="John Doe", key="patient_name")
                age = st.number_input("Age", min_value=0, max_value=150, step=1, 
                                   help="Patient's age in years", key="patient_age")
                gender = st.selectbox("Gender", ["Select", "Male", "Female", "Other"], key="patient_gender")
                
            with col2:
                weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1, 
                                      placeholder="e.g., 70.5", key="patient_weight")
                height = st.number_input("Height (cm)", min_value=0.0, step=0.1, 
                                      placeholder="e.g., 175.0", key="patient_height")
                blood_pressure = st.text_input("Blood Pressure", 
                                            placeholder="e.g., 120/80", key="patient_bp")
            
            st.divider()
            st.markdown("<h2>📊 Vital Signs</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            
            with col1:
                temperature = st.number_input("Temperature (°C)", min_value=30.0, 
                                           max_value=45.0, step=0.1, value=37.0, key="patient_temp")
            with col2:
                heart_rate = st.number_input("Heart Rate (bpm)", min_value=0, 
                                          max_value=200, step=1, value=72, key="patient_hr")
            with col3:
                respiratory_rate = st.number_input("Respiratory Rate (breaths/min)", 
                                                min_value=0, max_value=100, step=1, value=16, key="patient_rr")
            
            # Oxygen Level
            o2_level = st.slider("Oxygen Saturation (SpO₂ %)", min_value=70, max_value=100, 
                               value=98, step=1, key="patient_o2")
            
            st.divider()
            st.markdown("<h2>🤒 General Health Questions</h2>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                vision = st.selectbox("Can you see clearly without glasses?", 
                                   ["Yes", "No, I need glasses/contacts", "Partially"], 
                                   key="vision")
                hearing = st.selectbox("Do you have any difficulty in hearing?", 
                                    ["No", "Yes, mild difficulty", "Yes, significant difficulty"], 
                                    key="hearing")
                skin_condition = st.selectbox("Do you have any visible skin conditions?", 
                                           ["No", "Yes, mild", "Yes, moderate", "Yes, severe"], 
                                           key="skin_condition")
                
            with col2:
                breathing = st.selectbox("Do you experience difficulty in breathing?", 
                                      ["Never", "Occasionally", "Frequently", "Constantly"], 
                                      key="breathing")
                oral_health = st.selectbox("Do you experience any mouth conditions?",
                                        ["No", "Bleeding gums", "Bad breath", "Frequent mouth ulcers", "Tooth pain or sensitivity"], 
                                        key="oral_health")
                urine_color = st.selectbox("What is your usual urine color?",
                                        ["Clear", "Pale yellow", "Dark yellow", "Brownish/red (seek medical attention)"],
                                        key="urine_color")
            
            st.divider()
            st.markdown("<h2>📝 Additional Information</h2>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                hair_loss = st.selectbox("Have you noticed significant hair loss recently?",
                                      ["No", "Yes, mild hair loss", "Yes, moderate hair loss", "Yes, severe hair loss"],
                                      key="hair_loss")
                nail_changes = st.selectbox("Any changes in your nails?",
                                         ["No", "White spots", "Yellowing", "Dark streaks", "Brittle nails"],
                                         key="nail_changes")
            
            with col2:
                cataract = st.selectbox("Any signs of cataract or vision issues?",
                                     ["No", "Suspected cataract", "Diagnosed cataract", "Other vision issues"],
                                     key="cataract")
                disabilities = st.selectbox("Any physical disabilities?",
                                         ["No", "Mobility issues", "Visual impairment", "Hearing impairment", "Other"],
                                         key="disabilities")
            
            st.divider()
            symptoms = st.text_area("Describe any symptoms or concerns in detail", 
                                 placeholder="Enter the patient's symptoms, duration, severity, and any other relevant information...",
                                 height=100, key="symptoms")
            
            # Form submission
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                submit_button = st.form_submit_button("Generate Report", type="primary", 
                                                   use_container_width=True)
        
        if submit_button:
            # Basic validation
            if not all([name, age, gender != "Select", weight, height, blood_pressure]):
                st.error("Please fill in all required fields")
            else:
                # Prepare data for report generation
                patient_data = {
                    'patient_name': name,
                    'patient_age': age,
                    'patient_gender': gender,
                    'weight': weight,
                    'height': height,
                    'blood_pressure': blood_pressure,
                    'temperature': temperature,
                    'pulse_rate': heart_rate,
                    'respiratory_rate': respiratory_rate,
                    'o2_level': o2_level,
                    'vision': vision,
                    'hearing': hearing,
                    'skin_condition': skin_condition,
                    'breathing': breathing,
                    'oral_health': oral_health,
                    'urine_color': urine_color,
                    'hair_loss': hair_loss,
                    'nail_changes': nail_changes,
                    'cataract': cataract,
                    'disabilities': disabilities,
                    'symptoms': symptoms,
                    # Add current date and generate report ID
                    'collection_date': st.session_state.get('current_date', '2023-01-01'),
                    'report_date': st.session_state.get('current_date', '2023-01-01'),
                    'report_ID': f"RPT-{os.urandom(4).hex().upper()}",
                    'patient_ID': f"PAT-{os.urandom(4).hex().upper()}",
                    'patient_referee': "Self",
                    'patient_phone': "Not provided"
                }
                
                try:
                    # Generate and save the report
                    report_path = create_medical_report(patient_data)
                    save_response(patient_data)
                    
                    # Show success message and download button
                    st.success("✅ Report generated successfully!")
                    
                    # Add download button
                    with open(report_path, "rb") as f:
                        st.download_button(
                            label="📥 Download Report",
                            data=f,
                            file_name=f"medical_report_{patient_data['report_ID']}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    
                    # Show a preview of the generated data
                    with st.expander("View Generated Report Data"):
                        st.json(patient_data, expanded=False)
                        
                except Exception as e:
                    st.error(f"❌ Error generating report: {str(e)}")

def init_db():
    """Initialize the database with required tables if they don't exist"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create users table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create responses table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id SERIAL PRIMARY KEY,
                collection_date DATE,
                report_date DATE,
                report_id VARCHAR(50),
                patient_id VARCHAR(50),
                patient_name VARCHAR(100),
                patient_age_gender VARCHAR(50),
                patient_referee VARCHAR(100),
                patient_phone VARCHAR(20),
                weight FLOAT,
                height FLOAT,
                bmi FLOAT,
                pulse_rate INTEGER,
                blood_pressure VARCHAR(20),
                o2_level FLOAT,
                temperature FLOAT,
                vision TEXT,
                breathing TEXT,
                hearing TEXT,
                skin_condition TEXT,
                oral_health TEXT,
                urine_color TEXT,
                hair_loss TEXT,
                nail_changes TEXT,
                cataract TEXT,
                disabilities TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER REFERENCES users(id)
            )
        """)
        
        conn.commit()
        print("Database initialized successfully")
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

# Initialize database when the app starts
init_db()

# Main application flow
if _name_ == "_main_":
    # Add custom CSS for better styling
    st.markdown("""
    <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .stButton>button {
            width: 100%;
        }
        .stTextInput>div>div>input, 
        .stNumberInput>div>div>input,
        .stSelectbox>div>div>select {
            border-radius: 8px;
            border: 1px solid #ced4da;
        }
        .stTextArea>div>div>textarea {
            border-radius: 8px;
            border: 1px solid #ced4da;
        }
        .stAlert {
            border-radius: 8px;
        }
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: #4361ee;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre;
            background-color: #f0f2f6;
            border-radius: 8px 8px 0 0;
            gap: 8px;
            padding: 0 16px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #4361ee;
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Set the current date in session state if not set
    if 'current_date' not in st.session_state:
        st.session_state.current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Handle page routing
    if not st.session_state.get('authenticated'):
        login_page()
    else:
        report_generation_page()
        
        # Add logout button in the sidebar
        if st.sidebar.button("Logout", type="secondary"):
            st.session_state.authenticated = False
            st.session_state.current_page = "login"
            st.rerun()
def init_db():
    """Initialize the database with required tables if they don't exist"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create users table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create responses table if it doesn't exist
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
                weight NUMERIC(5,2),
                height NUMERIC(5,2),
                bmi NUMERIC(5,2),
                pulse_rate INTEGER,
                blood_pressure VARCHAR(20),
                o2_level VARCHAR(10),
                temperature NUMERIC(5,2),
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
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

# Initialize database when the app starts
init_db()

# Main application flow
if st.session_state.current_page == "login":
    login_page()
elif st.session_state.current_page == "generate_report":
    report_generation_page()