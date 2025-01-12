import streamlit as st
from fpdf import FPDF
import smtplib
from email.message import EmailMessage

# A user database
USER_CREDENTIALS = {
    "admin": "password123",
    "user1": "user1pass",
    "user2": "user2pass"
}


# Authentication function
def authenticate(username, password):
    return USER_CREDENTIALS.get(username) == password


# Define the PDF class
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'Medical Diagnostic Report', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, label):
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, f'{label}', 0, 1, 'L')

    def chapter_body(self, body):
        self.set_font('Helvetica', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()


# Function to generate the PDF
def create_medical_report(heart_rate, blood_pressure, o2_level, temperature, iron_level):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, 'Medical Results:', 0, 1)
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 10, f'Heart Rate: {heart_rate} bpm', 0, 1)
    pdf.cell(0, 10, f'Blood Pressure: {blood_pressure}', 0, 1)
    pdf.cell(0, 10, f'Oxygen Saturation: {o2_level}%', 0, 1)
    pdf.cell(0, 10, f'Temperature: {temperature}°F', 0, 1)
    pdf.cell(0, 10, f'Iron Level: {iron_level} mg/dL', 0, 1)
    pdf.ln(10)
    pdf.chapter_title('Risk Analysis')
    risks = (
        f"Anaemia: {'High Risk' if iron_level < 10 else 'Low Risk'}\n"
        f"Diabetes: {'High Risk' if heart_rate > 90 else 'Low Risk'}\n"
        f"Heart Conditions: {'High Risk' if heart_rate > 120 else 'Low Risk'}\n"
        f"Vitamin Deficiency: {'High Risk' if o2_level < 97 else 'Low Risk'}"
    )
    pdf.chapter_body(risks)

    # Concluding Statement
    conclusion = \
        "Concluding Advice: Maintain a balanced diet, regular exercise, and follow up with your physician regularly."
    pdf.chapter_title('Concluding Statement')
    pdf.chapter_body(conclusion)

    # Save PDF
    output_file = "generated_medical_report.pdf"
    pdf.output(output_file)
    return output_file


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
        st.write("Enter the following details to generate the report:")

        # Patient details
        patient_name = st.text_input("Patient Name:")
        patient_age = st.number_input("Patient Age:", min_value=0)
        patient_gender = st.selectbox("Patient Gender:", ["Select", "Male", "Female", "Other"])

        # Required inputs
        heart_rate = st.number_input("Heart Rate (bpm):", min_value=0)
        blood_pressure = st.number_input("Blood Pressure (mmHg):", min_value=0)
        o2_level = st.number_input("Oxygen Saturation (%):", min_value=0, max_value=100)
        temperature = st.number_input("Temperature (°F):", min_value=80.0, value=98.6)
        iron_level = st.number_input("Iron Level (mg/dL):", min_value=0)

        email = st.text_input("Email (optional):", placeholder="Enter email to send the report")

        # Submit button
        submit_button = st.form_submit_button(label="Generate PDF")

    # Form submission
    if submit_button:
        try:
            output_file = create_medical_report(heart_rate, blood_pressure, o2_level, temperature, iron_level)
            st.success("PDF generated successfully!")

            # Provide download link
            with open(output_file, "rb") as pdf_file:
                st.download_button(
                    label="Download PDF",
                    data=pdf_file,
                    file_name="medical_report.pdf",
                    mime="application/pdf"
                )

            # Send email if email is provided
            if email:
                st.info(f"Sending the report to {email}...")
                try:
                    msg = EmailMessage()
                    msg["Subject"] = "Medical Diagnostic Report"
                    msg["From"] = "10minutemail24@gmail.com"  # My email
                    msg["To"] = email
                    msg.set_content("Attached is your medical diagnostic report.")

                    with open(output_file, "rb") as pdf:
                        msg.add_attachment(pdf.read(), maintype="application",
                                           subtype="pdf", filename=f"medical_report_{patient_name}.pdf")

                    # Send the email (need to configure SMTP server)
                    with smtplib.SMTP("smtp.gmail.com", 587) as server:
                        server.starttls()
                        server.login("10minutemail24@gmail.com", "cngc yfqa diec texl")  # Credentials
                        server.send_message(msg)

                    st.success(f"Report sent to {email} successfully!")
                except Exception as e:
                    st.error(f"Failed to send email: {e}")
        except Exception as e:
            st.error(f"Failed to generate the PDF: {e}")

    # Logout button
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
