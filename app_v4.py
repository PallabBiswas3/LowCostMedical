import streamlit as st
import psycopg2
from psycopg2 import sql
from fpdf import FPDF
import smtplib
from email.message import EmailMessage

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


# Authentication function
def authenticate(username, password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username = %s", (username,))
    stored_password = cur.fetchone()
    conn.close()
    return stored_password and stored_password[0] == password


# PDF generation function
def create_medical_report(data):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14)
            self.cell(0, 10, 'TreeMed - Medical Report', 0, 1, 'C')
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, '~End of report~', 0, 0, 'C')

        def patient_info(self, details):
            self.set_font('Arial', '', 12)
            for key, value in details.items():
                self.cell(0, 10, f"{key}: {value}", 0, 1)
            self.ln(5)

        def test_results(self, tests):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, "Test Results:", 0, 1)
            self.set_font('Arial', '', 12)
            for key, value in tests.items():
                self.cell(0, 10, f"{key}: {value}", 0, 1)
            self.ln(10)

    pdf = PDF()
    pdf.add_page()
    pdf.patient_info({
        "Name": data['patient_name'],
        "Age/Gender": data['patient_age_gender'],
        "Referred By": data['patient_referee'],
        "Phone": data['patient_phone'],
        "Patient ID": data['patient_id'],
        "Report ID": data['report_id'],
        "Collection Date": data['collection_date'],
        "Report Date": data['report_date']
    })
    pdf.test_results({
        "SpO2": data['o2_level'],
        "Temperature": data['temperature'],
        "Pulse Rate": data['pulse_rate'],
        "Blood Pressure": data['blood_pressure']
    })

    output_file = "medical_report.pdf"
    pdf.output(output_file)
    return output_file


# Store response in database
def save_response(data):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO responses (
            collection_date, report_date, report_id, patient_id, patient_name,
            patient_age_gender, patient_referee, patient_phone, pulse_rate,
            blood_pressure, o2_level, temperature
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        data['collection_date'], data['report_date'], data['report_id'],
        data['patient_id'], data['patient_name'], data['patient_age_gender'],
        data['patient_referee'], data['patient_phone'], data['pulse_rate'],
        data['blood_pressure'], data['o2_level'], data['temperature']
    ))
    conn.commit()
    conn.close()


# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"


# Login page
def login_page():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login")

    if login_button:
        if authenticate(username, password):
            st.session_state.authenticated = True
            st.session_state.current_page = "generate_report"
            st.success("Login successful!")
        else:
            st.error("Invalid username or password.")


# Report generation page
def report_generation_page():
    st.title("Medical Diagnostic Report Generator")

    with st.form(key="input_form"):
        st.write("Enter patient details:")
        data = {
            "collection_date": st.text_input("Collection Date"),
            "report_date": st.text_input("Report Date"),
            "report_id": st.number_input("Report ID", min_value=0),
            "patient_id": st.number_input("Patient ID", min_value=0),
            "patient_name": st.text_input("Patient Name"),
            "patient_age_gender": st.text_input("Patient Age/Gender"),
            "patient_referee": st.text_input("Referred By"),
            "patient_phone": st.text_input("Phone Number"),
            "pulse_rate": st.number_input("Pulse Rate (bpm)", min_value=0),
            "blood_pressure": st.text_input("Blood Pressure (mmHg)"),
            "o2_level": st.text_input("SpO2 (%)"),
            "temperature": st.number_input("Temperature (°F)", min_value=80.0, value=98.6),
            "email": st.text_input("Email (optional)", placeholder="Enter email to send the report")
        }
        submit_button = st.form_submit_button("Generate PDF")

    if submit_button:
        try:
            save_response(data)
            output_file = create_medical_report(data)
            st.success("PDF generated successfully!")

            with open(output_file, "rb") as pdf_file:
                st.download_button(label="Download PDF",
                                   data=pdf_file,
                                   file_name="medical_report.pdf",
                                   mime="application/pdf")

            if data["email"]:
                st.info(f"Sending report to {data['email']}...")
                msg = EmailMessage()
                msg["Subject"] = "Medical Diagnostic Report"
                msg["From"] = "10minutemail24@gmail.com"
                msg["To"] = data["email"]
                msg.set_content("Attached is your medical diagnostic report.")

                with open(output_file, "rb") as pdf:
                    msg.add_attachment(pdf.read(), maintype="application", subtype="pdf", filename="medical_report.pdf")

                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login("10minutemail24@gmail.com", "cngc yfqa diec texl")
                    server.send_message(msg)

                st.success("Report sent successfully!")
        except Exception as e:
            st.error(f"Error: {e}")

    if st.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.current_page = "login"


# Main app logic
if st.session_state.current_page == "login":
    login_page()
elif st.session_state.current_page == "generate_report" and st.session_state.authenticated:
    report_generation_page()
else:
    st.session_state.current_page = "login"
    login_page()
