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


def create_medical_report(collection_date, report_date, patient_name, patient_age, patient_gender, patient_referee,
                          patient_phone, patient_ID, report_ID, o2_level, temperature, pulse_rate, blood_pressure):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14)
            self.image('logo.png', 10, 8, 33)
            self.cell(0, 10, '', ln=True)
            self.cell(0, 10, 'TreeMed', 0, 1, 'C')
            self.cell(0, 10, 'hello@treemed.in          +91 721302', 0, 1, 'C')
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, '~End of report~', 0, 0, 'C')

        def patient_info(self, left_info, right_info):
            self.set_font('Arial', '', 12)
            initial_y = self.get_y()
            self.multi_cell(95, 10, "\n".join([f"{k}: {v}" for k, v in left_info.items()]), 0, 'L')
            self.set_y(initial_y)
            self.set_x(105)
            self.multi_cell(95, 10, "\n".join([f"{k}: {v}" for k, v in right_info.items()]), 0, 'L')
            self.ln(10)

        def add_dates(self, left_date_info, right_date_info):
            self.set_font('Arial', '', 12)
            initial_y = self.get_y()
            self.multi_cell(95, 10, "\n".join([f"{k}: {v}" for k, v in left_date_info.items()]), 0, 'L')
            self.set_y(initial_y)
            self.set_x(105)
            self.multi_cell(95, 10, "\n".join([f"{k}: {v}" for k, v in right_date_info.items()]), 0, 'L')
            self.ln(10)
            self.set_draw_color(0, 0, 0)
            self.line(10, self.get_y(), 200, self.get_y())

        def flag_result(self, result, range_str):
            if '/' in result:
                result_systolic, result_diastolic = map(float, result.split('/'))
                range_systolic, range_diastolic = range_str.split(' - ')
                systolic_bounds = list(map(float, range_systolic.split('/')))
                diastolic_bounds = list(map(float, range_diastolic.split('/')))

                if not (systolic_bounds[0] <= result_systolic <= systolic_bounds[1]) or \
                        not (diastolic_bounds[0] <= result_diastolic <= diastolic_bounds[1]):
                    return 'Out of range'
            else:
                result = float(result.replace('%', ''))
                bounds = range_str.replace('%', '').split('-')
                lower_bound = float(bounds[0].strip())
                upper_bound = float(bounds[1].strip())

                if not (lower_bound <= result <= upper_bound):
                    return 'Out of range'
            return ''

        def chapter_title(self, title):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, title, 0, 1, 'L')

        def test_table(self, test_info):
            self.set_fill_color(200, 220, 255)
            self.set_font('Arial', 'B', 12)
            col_widths = [80, 30, 30, 30, 20]
            headers = ['TEST DESCRIPTION', 'RESULT', 'FLAG', 'REF. RANGE', 'UNIT']
            for i, header in enumerate(headers):
                self.cell(col_widths[i], 10, header, 1, 0, 'C', 1)
            self.ln()
            self.set_font('Arial', '', 12)
            for test in test_info:
                flag = self.flag_result(test['result'], test['range'])
                self.cell(col_widths[0], 10, test['description'], 1)
                self.cell(col_widths[1], 10, str(test['result']), 1)
                self.cell(col_widths[2], 10, flag, 1)
                self.cell(col_widths[3], 10, test['range'], 1)
                self.cell(col_widths[4], 10, test['unit'], 1)
                self.ln()

    # Create PDF object
    pdf = PDF()
    pdf.add_page()

    # Add date information
    date_info_left = {'Collection Date': collection_date}
    date_info_right = {'Report Date': report_date}
    pdf.add_dates(date_info_left, date_info_right)

    # Add patient information
    left_info = {
        'Name': patient_name,
        'Age/Gender': f'{patient_age}/{patient_gender}',
        'Referred By': patient_referee,
    }
    right_info = {
        'Phone No.': patient_phone,
        'Patient ID': patient_ID,
        'Report ID': report_ID,
    }
    pdf.patient_info(left_info, right_info)

    # Add chapter title
    pdf.chapter_title('General Body Checkup')

    # Test information
    test_info = [
        {'description': 'SpO2', 'result': o2_level, 'flag': '', 'range': '94-100%', 'unit': '%'},
        {'description': 'Temperature', 'result': temperature, 'flag': '', 'range': '97.8-99.1', 'unit': '°F'},
        {'description': 'Pulse Rate', 'result': pulse_rate, 'flag': '', 'range': '60-100', 'unit': 'bpm'},
        {'description': 'BP', 'result': blood_pressure, 'flag': '', 'range': '90/60 - 140/90', 'unit': 'mmHg'}
    ]
    pdf.test_table(test_info)

    # Output PDF
    pdf.output(f'medical_report_{patient_name}.pdf')


"""class PDF(FPDF):
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
def create_medical_report(patient_name, patient_age, patient_gender, collection_date, heart_rate,
                          blood_pressure, o2_level, temperature, iron_level):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, 'Medical Results:', 0, 1)
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 10, f'Name: {collection_date}', 0, 1)
    pdf.cell(0, 10, f'Name: {patient_name}', 0, 1)
    pdf.cell(0, 10, f'Age: {patient_age}', 0, 1)
    pdf.cell(0, 10, f'Gender: {patient_gender}', 0, 1)
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
    return output_file"""


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
        collection_date = st.text_input("PCollection Date:")
        report_date = st.text_input("Report:")
        report_ID = st.number_input("Report ID:", min_value=0)
        patient_ID = st.number_input("Patient ID:", min_value=0)
        patient_name = st.text_input("Patient Name:")
        patient_age = st.number_input("Patient Age:", min_value=0)
        patient_gender = st.selectbox("Patient Gender:", ["Select", "Male", "Female", "Other"])
        patient_referee = st.text_input("Referred by:")
        patient_phone = st.number_input("Patient Contact details:", min_value=0)

        # Required inputs
        pulse_rate = st.number_input("Pulse Rate (bpm):", min_value=0)
        blood_pressure = st.number_input("Blood Pressure (mmHg):", min_value=0)
        o2_level = st.number_input("Sp_O2 (%):", min_value=0, max_value=100)
        temperature = st.number_input("Temperature (°F):", min_value=80.0, value=98.6)

        email = st.text_input("Email (optional):", placeholder="Enter email to send the report")

        # Submit button
        submit_button = st.form_submit_button(label="Generate PDF")

    # Form submission
    if submit_button:
        try:
            output_file = (
                create_medical_report(collection_date, report_date, patient_name, patient_age, patient_referee,
                                      patient_phone, patient_ID, report_ID, o2_level,
                                      temperature, pulse_rate, blood_pressure))
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
