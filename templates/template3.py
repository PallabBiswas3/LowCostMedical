from fpdf import FPDF
import streamlit as st


def create_medical_report(collection_date, report_date, patient_name, patient_age_gender, patient_referee,
                          patient_phone, patient_ID, report_ID, o2_level, temperature, pulse_Rate, blood_pressure,
                          vision, breathing, hearing, skin_condition, oral_health, urine_color, hair_loss,
                          nail_changes, cataract, disabilities):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14)
            self.image('../assets/logo.png', 10, 8, 33)
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
            self.line(10, self.get_y(), 200, self.get_y())
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

        @staticmethod
        def flag_result(self, result, range_str):
            try:
                if '/' in result:
                    # Handle blood pressure-like values (e.g., "120/80")
                    result_systolic, result_diastolic = map(float, result.split('/'))
                    range_systolic, range_diastolic = range_str.split(' - ')
                    systolic_bounds = list(map(float, range_systolic.split('/')))
                    diastolic_bounds = list(map(float, range_diastolic.split('/')))

                    if not (systolic_bounds[0] <= result_systolic <= systolic_bounds[1]) or \
                            not (diastolic_bounds[0] <= result_diastolic <= diastolic_bounds[1]):
                        return 'Out of range'

                else:
                    # Handle single values (e.g., "94%", "85-100")
                    result = float(result.replace('%', '').strip())

                    # Ensure range is properly formatted
                    if '-' in range_str:
                        bounds = range_str.replace('%', '').split('-')
                        lower_bound = float(bounds[0].strip())
                        upper_bound = float(bounds[1].strip())

                        if not (lower_bound <= result <= upper_bound):
                            return 'Out of range'

                return ''  # In range
            except (ValueError, IndexError):
                return 'Invalid input'

        def chapter_title(self, title):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, title, 0, 1, 'L')

        def test_table_1(self, test_info):
            self.set_fill_color(200, 220, 255)
            self.set_font('Arial', 'B', 12)
            col_widths = [80, 30, 30, 30, 20]
            headers = ['TEST DESCRIPTION', 'RESULT', 'FLAG', 'REF. RANGE', 'UNIT']
            for i, header in enumerate(headers):
                self.cell(col_widths[i], 10, header, 1, 0, 'C', True)
            self.ln()
            self.set_font('Arial', '', 12)
            for test in test_info:
                flag = self.flag_result(test['result'], test['range'], range_str=2000)
                self.cell(col_widths[0], 10, test['description'], 1)
                self.cell(col_widths[1], 10, str(test['result']), 1)
                self.cell(col_widths[2], 10, flag, 1)
                self.cell(col_widths[3], 10, test['range'], 1)
                self.cell(col_widths[4], 10, test['unit'], 1)
                self.ln()

        def test_table_2(self, test_info):
            self.set_fill_color(200, 220, 255)
            self.set_font('Arial', 'B', 12)
            col_widths = [20, 120, 50]
            headers = ['Sl. No.', 'QUESTIONS', 'SELECTED OPTION']
            for i, header in enumerate(headers):
                self.cell(col_widths[i], 10, header, 1, 0, 'C', True)
            self.ln()
            self.set_font('Arial', '', 12)
            for i, test in enumerate(test_info):
                # flag = self.flag_result(test['result'], test['range'], range_str=2000)
                self.cell(col_widths[0], 10, str(i+1)+'.', 1, align='C')
                self.cell(col_widths[1], 10, test['description'], 1)
                self.cell(col_widths[2], 10, test['result'], 1)
                # self.cell(col_widths[2], 10, flag, 1)
                # self.cell(col_widths[3], 10, test['range'], 1)
                # self.cell(col_widths[4], 10, test['unit'], 1)
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
        'Age/Gender': patient_age_gender,
        'Referred By': patient_referee,
    }
    right_info = {
        'Phone No.': patient_phone,
        'Patient ID': patient_ID,
        'Report ID': report_ID,
    }
    pdf.patient_info(left_info, right_info)

    # Add chapter title
    pdf.chapter_title('Body Vitals')

    # Vitals Test information
    test_info_vitals = [
        {'description': 'SpO2', 'result': o2_level, 'flag': '', 'range': '94-100%', 'unit': '%'},
        {'description': 'Temperature', 'result': temperature, 'flag': '', 'range': '97.8-99.1', 'unit': '°F'},
        {'description': 'Pulse Rate', 'result': pulse_Rate, 'flag': '', 'range': '60-100', 'unit': 'bpm'},
        {'description': 'BP', 'result': blood_pressure, 'flag': '', 'range': '90/60 - 140/90', 'unit': 'mmHg'}
    ]
    pdf.test_table_1(test_info_vitals)

    # Add chapter title
    pdf.chapter_title('General Questions')

    # General Questions
    test_info_general = [
        {'description': "Can you see clearly without glasses?", 'result': vision},
        {'description': "Do you experience difficulty in breathing?", 'result': breathing},
        {'description': "Do you have any difficulty in hearing?", 'result': hearing},
        {'description': "Do you have any visible skin conditions?", 'result': skin_condition},
        {'description': "Do you experience any mouth conditions?", 'result': oral_health},
        {'description': "What is your usual urine colour?", 'result': urine_color},
        {'description': "Have you noticed significant hair loss recently?", 'result': hair_loss},
        {'description': "Have you noticed any unusual changes in your nail colour?", 'result': nail_changes},
        {'description': "Have you been diagnosed with or noticed signs of cataract?", 'result': cataract},
        {'description': "Do you have any physical disabilities?", 'result': disabilities}

    ]
    pdf.test_table_2(test_info_general)

    # Output PDF
    output_file = "../generated_files/medical_report.pdf"
    pdf.output(output_file)
    return output_file


# Example usage
def main():
    st.title("Medical Diagnostic Report Generator")

    with st.form(key="input_form"):
        st.write("Enter the following details to generate the report:")

        # Patient details
        collection_date = st.text_input("Collection Date:")
        report_date = st.text_input("Report Date:")
        report_ID = st.number_input("Report ID:", min_value=0)
        patient_ID = st.number_input("Patient ID:", min_value=0)
        patient_name = st.text_input("Patient Name:")
        patient_age_gender = st.text_input("Patient Age/Gender:")
        patient_referee = st.text_input("Referred by:")
        patient_phone = st.number_input("Patient Contact details:", min_value=0)

        # Required vitals inputs
        pulse_rate = st.number_input("Pulse Rate (bpm):", min_value=0)
        blood_pressure = st.text_input("Blood Pressure (mmHg):")
        o2_level = st.text_input("Sp_O2 (%):")
        temperature = st.number_input("Temperature (°F):", min_value=80.0, value=98.6)

        # General questions
        vision = st.radio("Can you see clearly without glasses?",
                          ["Yes",
                           "No",
                           "Not Sure"])
        breathing = st.radio("Do you experience difficulty in breathing?",
                             ["No difficulty",
                              "Often, even at rest",
                              "Occasionally, during physical activity",
                              "Only during certain conditions"])
        hearing = st.radio("Do you have any difficulty in hearing?",
                           ["No", "Yes, in one ear", "Yes, in both ears", "Not Sure"])
        skin_condition = st.radio("Do you have any visible skin conditions?",
                                  ["Not Sure",
                                   "Yes, mild",
                                   "Yes, moderate",
                                   "Yes, severe"])
        oral_health = st.radio("Do you experience any mouth conditions?",
                               ["No issues",
                                "Bleeding gums",
                                "Bad breath",
                                "Frequent mouth ulcers",
                                "Tooth pain or sensitivity"])
        urine_color = st.radio("What is your usual urine colour?",
                               ["Clear",
                                "Pale yellow",
                                "Dark yellow",
                                "Brownish/red (seek medical attention)"])
        hair_loss = st.radio("Have you noticed significant hair loss recently?",
                             ["No",
                              "Yes, mild hair loss",
                              "Yes, moderate hair loss",
                              "Yes, severe hair loss"])
        nail_changes = st.radio("Have you noticed any unusual changes in your nail colour?",
                                ["No",
                                 "Yes, white spots",
                                 "Yes, yellowing",
                                 "Yes, dark streaks"])
        cataract = st.radio("Have you been diagnosed with or noticed signs of cataract?",
                            ["No",
                             "Yes, diagnosed by a doctor",
                             "Yes, not diagnosed yet"])
        disabilities = st.radio("Do you have any physical disabilities?",
                                ["No",
                                 "Yes, partial mobility issues",
                                 "Yes, require walking aids",
                                 "Yes, fully dependent on assistance"])

        # email = st.text_input("Email (optional):", placeholder="Enter email to send the report")

        # Submit button
        submit_button = st.form_submit_button(label="Generate PDF")

    # Form submission
    if submit_button:
        try:
            output_file = (
                create_medical_report(collection_date, report_date, patient_name, patient_age_gender, patient_referee,
                                      patient_phone, patient_ID, report_ID, o2_level, temperature, pulse_rate,
                                      blood_pressure, vision, breathing, hearing, skin_condition, oral_health,
                                      urine_color, hair_loss, nail_changes, cataract, disabilities)
            )
            st.success("PDF generated successfully!")

            # Provide download link
            with open(output_file, "rb") as pdf_file:
                st.download_button(
                    label="Download PDF",
                    data=pdf_file,
                    file_name="../medical_report.pdf",
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"Failed to generate the PDF: {e}")


if __name__ == "__main__":
    main()
