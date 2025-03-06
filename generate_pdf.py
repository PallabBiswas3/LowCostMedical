from fpdf import FPDF


def create_medical_report(data):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14)
            self.image('assets/logo.png', 10, 8, 33)
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
                    # handle single values ("94%", "85-100")
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
            headers = ['VITALS', 'RESULT', 'FLAG', 'REF. RANGE', 'UNIT']
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
                self.cell(col_widths[0], 10, str(i+1)+'.', 1, align='C')
                self.cell(col_widths[1], 10, test['description'], 1)
                self.cell(col_widths[2], 10, test['result'], 1)
                self.ln()

    pdf = PDF()
    pdf.add_page()

    # Add date information
    date_info_left = {'Collection Date': data['collection_date']}
    date_info_right = {'Report Date': data['report_date']}
    pdf.add_dates(date_info_left, date_info_right)

    # Add patient information
    left_info = {
        'Name': data['patient_name'],
        'Age/Gender': data['patient_age_gender'],
        'Referred By': data['patient_referee']
    }
    right_info = {
        'Phone No.': data['patient_phone'],
        'Patient ID': str(data['patient_ID']),
        'Report ID': data['report_ID'],
    }
    pdf.patient_info(left_info, right_info)

    # Add chapter title
    pdf.chapter_title('Body Vitals')

    # Vitals Test information
    test_info_vitals = [
        {'description': 'SpO2', 'result': data['o2_level'], 'flag': '', 'range': '94-100%', 'unit': '%'},
        {'description': 'Temperature', 'result': data['temperature'], 'flag': '', 'range': '97.8-99.1', 'unit': '°F'},
        {'description': 'Pulse Rate', 'result': data['pulse_rate'], 'flag': '', 'range': '60-100', 'unit': 'bpm'},
        {'description': 'BP', 'result': data['blood_pressure'], 'flag': '', 'range': '90/60 - 140/90', 'unit': 'mmHg'}
    ]
    pdf.test_table_1(test_info_vitals)

    # Add chapter title
    pdf.chapter_title('General Questions')

    # General Questions
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

    # Output file
    output_file = "generated_files/medical_report.pdf"
    pdf.output(output_file)
    return output_file
