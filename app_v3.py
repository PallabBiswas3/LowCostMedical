import streamlit as st
import psycopg2
from fpdf import FPDF
import smtplib
from email.message import EmailMessage

# Database connection
DB_NAME = "Solar_med"
DB_USER = "postgres"
DB_PASSWORD = "Ankana@Postgres17"
DB_HOST = "localhost"


def connect_db():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)


def authenticate(username, password):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username = %s", (username,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result and result[0] == password


def store_response(data):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO responses (
      collection_date, report_date, patient_name, patient_age_gender, referee, phone, 
      patient_id, report_id, o2_level, temperature, pulse_rate, blood_pressure, email
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
  """, data)
    conn.commit()
    cur.close()
    conn.close()


def create_medical_report(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(200, 10, 'Medical Report', ln=True, align='C')
    pdf.ln(10)

    labels = [
        "Collection Date", "Report Date", "Patient Name", "Age/Gender", "Referred By", "Phone",
        "Patient ID", "Report ID", "SpO2", "Temperature", "Pulse Rate", "Blood Pressure"
    ]

    for label, value in zip(labels, data[:-1]):
        pdf.cell(0, 10, f"{label}: {value}", ln=True)

    output_file = "generated_report.pdf"
    pdf.output(output_file)
    return output_file


# Streamlit UI
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def login_page():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate(username, password):
            st.session_state.authenticated = True
            st.success("Login successful!")
        else:
            st.error("Invalid username or password.")


def report_page():
    st.title("Medical Report Generator")

    with st.form("report_form"):
        collection_date = st.text_input("Collection Date")
        report_date = st.text_input("Report Date")
        report_ID = st.number_input("Report ID", min_value=0)
        patient_ID = st.number_input("Patient ID", min_value=0)
        patient_name = st.text_input("Patient Name")
        age_gender = st.text_input("Age/Gender")
        referee = st.text_input("Referred By")
        phone = st.text_input("Phone")
        pulse_rate = st.number_input("Pulse Rate (bpm)", min_value=0)
        blood_pressure = st.text_input("Blood Pressure (mmHg)")
        o2_level = st.text_input("SpO2 (%)")
        temperature = st.number_input("Temperature (°F)", min_value=80.0, value=98.6)
        email = st.text_input("Email (optional)")
        submit = st.form_submit_button("Generate Report")

    if submit:
        data = (collection_date, report_date, patient_name, age_gender, referee, phone, patient_ID, report_ID, o2_level,
                temperature, pulse_rate, blood_pressure, email)
        store_response(data)
        pdf_file = create_medical_report(data)
        st.success("Report generated successfully!")
        with open(pdf_file, "rb") as pdf:
            st.download_button("Download PDF", data=pdf, file_name="medical_report.pdf", mime="application/pdf")


if not st.session_state.authenticated:
    login_page()
else:
    report_page()