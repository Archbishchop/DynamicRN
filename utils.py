import pandas as pd
import smtplib
import os
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from io import StringIO, BytesIO
import csv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def check_email_configuration():
    """Check if all required email settings are configured"""
    required_settings = ['SMTP_SERVER', 'SMTP_PORT', 'SENDER_EMAIL', 'SENDER_PASSWORD']
    missing_settings = [setting for setting in required_settings if not os.getenv(setting)]

    if missing_settings:
        error_msg = "Missing email configuration: " + ", ".join(missing_settings)
        logger.error(error_msg)
        return False, error_msg
    return True, None

def verify_smtp_connection():
    """Test SMTP connection and authentication with Office 365"""
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'outlook.office365.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL')
        sender_password = os.getenv('SENDER_PASSWORD')

        if not all([smtp_server, smtp_port, sender_email, sender_password]):
            return False, "Missing email configuration settings"

        logger.info(f"Testing connection to {smtp_server}:{smtp_port}")

        # Create SMTP session for testing
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()

        # Try to login
        try:
            server.login(sender_email, sender_password)
            server.quit()
            logger.info("Office 365 authentication successful")
            return True, None
        except smtplib.SMTPAuthenticationError as e:
            if "535" in str(e):  # Office 365 specific auth error
                error_msg = """
                Office 365 authentication failed. If you use Multi-Factor Authentication (MFA):
                1. You need to create an App Password
                2. Regular password won't work with MFA
                3. Go to Office 365 Account Settings → Security → App Passwords
                """
            else:
                error_msg = "Authentication failed: Please verify your Office 365 credentials"
            logger.error(f"{error_msg}: {str(e)}")
            return False, error_msg
    except Exception as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def send_email(to_email, subject, body):
    """Send email using SMTP"""
    try:
        # First verify configuration
        config_ok, config_error = check_email_configuration()
        if not config_ok:
            return False, config_error

        # Get email credentials
        smtp_server = os.getenv('SMTP_SERVER', 'outlook.office365.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL')
        sender_password = os.getenv('SENDER_PASSWORD')

        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Create SMTP session
        logger.info(f"Connecting to SMTP server: {smtp_server}:{smtp_port}")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()

        try:
            logger.info("Attempting SMTP login...")
            server.login(sender_email, sender_password)
            logger.info("SMTP login successful")

            # Send email
            server.send_message(msg)
            server.quit()
            logger.info(f"Email sent successfully to {to_email}")
            return True, None
        except smtplib.SMTPAuthenticationError as e:
            error_msg = "Failed to authenticate with Office 365. Please verify your credentials."
            logger.error(f"{error_msg}: {str(e)}")
            return False, error_msg
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    except Exception as e:
        error_msg = f"Error sending email: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def process_file_upload(file_content, file_type, db_session, field_mapping):
    """Process uploaded CSV or Excel file and import contacts"""
    try:
        logger.info(f"Starting file import process. File type: {file_type}")
        logger.info(f"Field mapping: {field_mapping}")

        # Read file content based on type
        if file_type == 'csv':
            df = pd.read_csv(StringIO(file_content.decode('utf-8')))
        else:  # Excel
            df = pd.read_excel(BytesIO(file_content))

        logger.info(f"File read successfully. Found {len(df)} rows")

        success_count = 0
        error_count = 0
        error_messages = []

        # Process each row
        for index, row in df.iterrows():
            try:
                # Map fields according to user's selection
                contact_data = {}
                for db_field, file_field in field_mapping.items():
                    if file_field in row:
                        # Convert NaN values to None
                        value = row[file_field]
                        contact_data[db_field] = None if pd.isna(value) else str(value).strip()
                        logger.info(f"Mapped {file_field} to {db_field}: {contact_data[db_field]}")

                # Validate required fields
                if not all([
                    contact_data.get('first_name'),
                    contact_data.get('last_name'),
                    contact_data.get('email')
                ]):
                    raise ValueError(f"Missing required fields: {contact_data}")

                # Validate email
                if not validate_email(contact_data.get('email', '')):
                    raise ValueError(f"Invalid email format: {contact_data['email']}")

                # Convert certifications to list if present
                if 'certifications' in contact_data and contact_data['certifications']:
                    if isinstance(contact_data['certifications'], str):
                        contact_data['certifications'] = [
                            cert.strip() 
                            for cert in contact_data['certifications'].split(',')
                            if cert.strip()
                        ]
                    else:
                        contact_data['certifications'] = []

                # Create new contact
                from models import Contact
                new_contact = Contact(**contact_data)
                db_session.add(new_contact)
                success_count += 1
                logger.info(f"Successfully processed row {index + 2}")

            except Exception as e:
                error_count += 1
                error_msg = f"Row {index + 2}: {str(e)}"
                logger.error(error_msg)
                error_messages.append(error_msg)

        # Commit all successful imports
        if success_count > 0:
            logger.info(f"Committing {success_count} contacts to database")
            try:
                db_session.commit()
            except Exception as e:
                logger.error(f"Database commit error: {str(e)}")
                return 0, success_count, [f"Failed to save contacts: {str(e)}"]

        logger.info(f"Import complete. Successes: {success_count}, Errors: {error_count}")
        return success_count, error_count, error_messages

    except Exception as e:
        logger.error(f"File processing error: {str(e)}")
        return 0, 0, [f"File processing error: {str(e)}"]