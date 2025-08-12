import streamlit as st
import smtplib
from email.message import EmailMessage
from PyPDF2 import PdfMerger
import psycopg2


# Database connection
DB_CONFIG = {
    "dbname": "Solar_med",
    "user": "postgres",
    "password": "Ankana@Postgres17",
    "host": "localhost",
    "port": "5432"
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


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
            patient_age_gender, patient_referee, patient_phone, pulse_rate,
            blood_pressure, o2_level, temperature, vision1, breathing, hearing, 
            skin_condition, oral_health, urine_color, hair_loss, nail_changes, 
            cataract, disabilities
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        data['collection_date'], data['report_date'], data['report_ID'],
        data['patient_ID'], data['patient_name'], data['patient_age_gender'],
        data['patient_referee'], data['patient_phone'], data['pulse_rate'],
        data['blood_pressure'], data['o2_level'], data['temperature'],
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


def login_page():
    st.markdown("""
        <style>
            body {
                background-color: #f5f5f5;
            }
            .login-box {
                background-color: #ffffff;
                padding: 30px 30px;
                width: 700px;
                margin: 10px auto;
                border-radius: 12px;
                box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
            }
            .login-title {
                font-size:30px;
                font-weight: 800;
                text-align: center;
                margin-bottom: 20px;
                color: #333333;
            }
            .stTextInput > div > div > input {
                padding: 20px;
                border-radius: 6px;
                border: 1px solid #ccc;
            }
            .stButton > button {
                background-color: #0077cc;
                color: white;
                padding: 12px 0;
                font-size: 16px;
                border-radius: 6px;
                font-weight: bold;
                width: 20%;
                margin-top: 10px;
                justify: center;
            }
        </style>

        <div class="login-box">
            <div class="login-title">Solar-Powered Mobile Health Measurement Device</div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate(username, password):
            st.session_state.authenticated = True
            st.session_state.current_page = "generate_report"
            st.success("Login successful!")
        else:
            st.error("Invalid credentials")


def report_generation_page():
    st.title("Medical Diagnostic Report Generator")

    final_pdf_path = None
    # uploaded_pdf = None
    with st.form(key="input_form"):
        st.write("Enter patient details:")
        data = {
            "collection_date": st.text_input("Collection Date", value="2025-04-15"),
            "report_date": st.text_input("Report Date", value="2025-04-15"),
            "report_ID": st.number_input("Report ID", min_value=0, value=1001),
            "patient_ID": st.number_input("Patient ID", min_value=0, value=5001),
            "patient_name": st.text_input("Patient Name", value="John Doe"),
            "patient_age_gender": st.text_input("Patient Age/Gender", value="30/M"),
            "patient_referee": st.text_input("Referred By", value="Dr. Smith"),
            "patient_phone": st.text_input("Phone Number", value="9876543210"),
            "email": st.text_input("Email (optional)", value="", placeholder="Enter email to send the report"),
            "weight": st.number_input("Weight (kg)", min_value=0),
            "height": st.number_input("Height (cm)", min_value=0),
            "pulse_rate": st.number_input("Pulse Rate (bpm)", min_value=0, value=72),
            "blood_pressure": st.text_input("Blood Pressure (mmHg)", value="120/80"),
            "o2_level": st.text_input("SpO2 (%)", value="98"),
            "temperature": st.number_input("Temperature (°F)", min_value=80.0, value=98.6),
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

    merged_pdf_path = None
    if submit:
        try:
            output_file = create_medical_report(data)
            st.success("PDF generated successfully!")

            # If a pdf is uploaded merge it
            if uploaded_pdf is not None:
                merger = PdfMerger()
                merger.append(output_file)

                # save uploaded pdf to a temp file
                uploaded_path = "generated_files/uploaded.pdf"
                with open(uploaded_path, "wb") as f:
                    f.write(uploaded_pdf.read())

                merger.append(uploaded_path)
                merged_pdf_path = "generated_files/merged_report.pdf"
                merger.write(merged_pdf_path)
                merger.close()

                st.session_state['final_pdf'] = merged_pdf_path
            else:
                st.session_state['final_pdf'] = output_file
            final_pdf_path = merged_pdf_path if merged_pdf_path else output_file

        except Exception as e:
            st.error(f"Error generating report: {str(e)}")
            st.session_state['final_pdf'] = None

    # download button(outside the form)
    if st.session_state.get('final_pdf'):
        with open(st.session_state['final_pdf'], "rb") as pdf_file:
            st.download_button(
                label="Download PDF",
                data=pdf_file,
                file_name="medical_report.pdf",
                mime="application/pdf"
            )
    # after pdf generation and optional merging
    if data["email"] and final_pdf_path:
        try:
            st.info(f"Sending report to {data['email']}...")
            msg = EmailMessage()
            msg["Subject"] = "Medical Diagnostic Report"
            msg["From"] = "10minutemail24@gmail.com"
            msg["To"] = data["email"]
            msg.set_content("Attached is your medical diagnostic report.")

            with open(final_pdf_path, "rb") as pdf:
                msg.add_attachment(pdf.read(), maintype="application", subtype="pdf", filename="medical_report.pdf")

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login("10minutemail24@gmail.com", "cngc yfqa diec texl")
                server.send_message(msg)

            st.success("Report sent successfully!")
        except (smtplib.SMTPException, FileNotFoundError, OSError) as e:

            st.error(f"Error sending report: {str(e)}")

    if st.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.current_page = "login"


if st.session_state.current_page == "login":
    login_page()
elif st.session_state.current_page == "generate_report":
    report_generation_page()
