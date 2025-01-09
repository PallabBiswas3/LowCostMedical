import streamlit as st
import subprocess

# A user database
USER_CREDENTIALS = {
    "admin": "password123",
    "user1": "user1pass",
    "user2": "user2pass"
}


# Authentication function
def authenticate(username, password):
    return USER_CREDENTIALS.get(username) == password


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
        # PDF file path
        output_file = "generated_medical_report.pdf"

        try:
            command = [
                "python", "generate_pdf.py",
                "--heart_rate", str(heart_rate),
                "--blood_pressure", str(blood_pressure),
                "--o2_level", str(o2_level),
                "--temperature", str(temperature),
                "--iron_level", str(iron_level),
                "--output", output_file
            ]
            subprocess.run(command, check=True)

            # Display success message
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
                import smtplib
                from email.message import EmailMessage

                st.info(f"Sending the report to {email}...")
                try:
                    msg = EmailMessage()
                    msg["Subject"] = "Medical Diagnostic Report"
                    msg["From"] = "email@gmail.com"  # Replace with your email
                    msg["To"] = email
                    msg.set_content("Attached is your medical diagnostic report.")

                    with open(output_file, "rb") as pdf:
                        msg.add_attachment(pdf.read(), maintype="application",
                                           subtype="pdf", filename="medical_report.pdf")

                    # Send the email (need to configure SMTP server)
                    with smtplib.SMTP("smtp.gmail.com", 587) as server:
                        server.starttls()
                        server.login("email@gmail.com", "password")  # Replace with credentials
                        server.send_message(msg)

                    st.success(f"Report sent to {email} successfully!")
                except Exception as e:
                    st.error(f"Failed to send email: {e}")
        except subprocess.CalledProcessError as e:
            st.error(f"Failed to generate the PDF: {e}")

    # Logout
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
