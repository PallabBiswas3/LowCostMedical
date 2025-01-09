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


def create_medical_report(output_path, heart_rate, blood_pressure, o2_level, temperature, iron_level):
    # Risk Analysis
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
    risks = (
        f"Anaemia: {risk_anaemia}\n"
        f"Diabetes: {risk_diabetes}\n"
        f"Heart Conditions: {risk_heart_conditions}\n"
        f"Vitamin Deficiency: {risk_vitamin_deficiency}"
    )
    pdf.chapter_body(risks)

    # Concluding Statement
    conclusion = "Concluding Advice: Maintain a balanced diet, regular exercise, and follow up with your physician regularly."
    pdf.chapter_title('Concluding Statement')
    pdf.chapter_body(conclusion)

    # Save PDF
    pdf.output(output_path)
    return output_path


if __name__ == "__main__":
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate a medical diagnostic report PDF.")
    parser.add_argument("--heart_rate", type=int, required=True, help="Heart rate in bpm")
    parser.add_argument("--blood_pressure", type=int, required=True, help="Blood pressure in mmHg")
    parser.add_argument("--o2_level", type=int, required=True, help="Oxygen saturation in percentage")
    parser.add_argument("--temperature", type=float, required=True, help="Body temperature in °F")
    parser.add_argument("--iron_level", type=int, required=True, help="Iron level in mg/dL")
    parser.add_argument("--output", type=str, default="medical_report.pdf", help="Output PDF file path")

    args = parser.parse_args()

    # Generate the PDF
    create_medical_report(
        output_path=args.output,
        heart_rate=args.heart_rate,
        blood_pressure=args.blood_pressure,
        o2_level=args.o2_level,
        temperature=args.temperature,
        iron_level=args.iron_level,
    )
    print(f"Medical report generated: {args.output}")
