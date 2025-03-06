from fpdf import FPDF


def create_medical_report(collection_date, report_date, patient_name, patient_age_gender, patient_referee, patient_phone, patient_ID, report_ID, o2_level, temperature, pulse_Rate, blood_pressure):
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
    pdf.chapter_title('General Body Checkup')

    # Test information
    test_info = [
        {'description': 'SpO2', 'result': o2_level, 'flag': '', 'range': '94-100%', 'unit': '%'},
        {'description': 'Temperature', 'result': temperature, 'flag': '', 'range': '97.8-99.1', 'unit': '°F'},
        {'description': 'Pulse Rate', 'result': pulse_Rate, 'flag': '', 'range': '60-100', 'unit': 'bpm'},
        {'description': 'BP', 'result': blood_pressure, 'flag': '', 'range': '90/60 - 140/90', 'unit': 'mmHg'}
    ]
    pdf.test_table(test_info)

    # Output PDF
    pdf.output('treemed_report.pdf')


# Example usage
create_medical_report(
    collection_date='03/05/2024 10:41 AM',
    report_date='03/05/2024 10:43 AM',
    patient_name='Mr. Ayusheee',
    patient_age_gender='23 Years/Male',
    patient_referee='Self',
    patient_phone='6397228160',
    patient_ID='240329001',
    report_ID='RE378',
    o2_level='98%',
    temperature='98.6',
    pulse_Rate='72',
    blood_pressure='120/80'
)