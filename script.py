import streamlit as st
from fpdf import FPDF


# Define the PDF class
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Medical Diagnostic Report', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, label):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, f'{label}', 0, 1, 'L')

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()


st.title('Medical Data Analysis')

with st.form(key='medical_form'):
    st.write("Please enter the following data:")
    heart_rate = st.number_input('Heart Rate (bpm)', min_value=0, value=70)
    blood_pressure = st.number_input('Blood Pressure (mmHg)', min_value=0, value=120)
    o2_level = st.number_input('Oxygen Saturation (%)', min_value=0, max_value=100, value=98)
    temperature = st.number_input('Temperature (°F)', min_value=80.0, value=98.6)
    iron_level = st.number_input('Iron Level (mg/dL)', min_value=0, value=50)
    submit_button = st.form_submit_button(label='Calculate')

if submit_button:
    risk_anaemia = "High Risk" if iron_level < 10 else "Low Risk"
    risk_diabetes = "High Risk" if heart_rate > 90 else "Low Risk"
    risk_heart_conditions = "High Risk" if heart_rate > 120 else "Low Risk"
    risk_vitamin_deficiency = "High Risk" if o2_level < 97 else "Low Risk"

    # Generate PDF
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Medical Results:', 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f'Heart Rate: {heart_rate} bpm', 0, 1)
    pdf.cell(0, 10, f'Blood Pressure: {blood_pressure}', 0, 1)
    pdf.cell(0, 10, f'Oxygen Saturation: {o2_level}%', 0, 1)
    pdf.cell(0, 10, f'Temperature: {temperature}°F', 0, 1)
    pdf.cell(0, 10, f'Iron Level: {iron_level} mg/dL', 0, 1)
    pdf.ln(10)
    pdf.chapter_title('Risk Analysis')
    risks = f'Anaemia: {risk_anaemia}\nDiabetes: {risk_diabetes}\nHeart Conditions: {risk_heart_conditions}\nVitamin Deficiency: {risk_vitamin_deficiency}'
    pdf.chapter_body(risks)

    # Concluding Statement
    conclusion = "Concluding Advice: Maintain a balanced diet, regular exercise, and follow up with your physician regularly."
    pdf.chapter_title('Concluding Statement')
    pdf.chapter_body(conclusion)

    # Save PDF to a temporary file
    pdf.output('medical_report.pdf')

    # Display results and provide download link
    st.subheader('Results:')
    st.write(f"Risk of Anaemia: {risk_anaemia}")
    st.write(f"Risk of Diabetes: {risk_diabetes}")
    st.write(f"Risk of Heart Conditions: {risk_heart_conditions}")
    st.write(f"Risk of Vitamin Deficiency: {risk_vitamin_deficiency}")
    with open("medical_report.pdf", "rb") as file:
        btn = st.download_button(
            label="Download Medical Report",
            data=file,
            file_name="medical_report.pdf",
            mime="application/pdf"
        )
