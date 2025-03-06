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

    # For Exchange, suggest default settings if not configured
    if missing_settings:
        if not os.getenv('SMTP_SERVER'):
            logger.info("SMTP server not configured, default Exchange server would be outlook.office365.com")
        if not os.getenv('SMTP_PORT'):
            logger.info("SMTP port not configured, default Exchange port would be 587")

    return len(missing_settings) == 0

def process_file_upload(file_content, file_type, db_session, field_mapping):
    """Process uploaded CSV or Excel file and import contacts"""
    try:
        # Read file content based on type
        if file_type == 'csv':
            df = pd.read_csv(StringIO(file_content.decode('utf-8')))
        else:  # Excel
            df = pd.read_excel(BytesIO(file_content))

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
                        contact_data[db_field] = row[file_field]

                # Validate required fields
                if not all([
                    contact_data.get('first_name'),
                    contact_data.get('last_name'),
                    contact_data.get('email')
                ]):
                    raise ValueError("Missing required fields")

                # Validate email
                if not validate_email(contact_data['email']):
                    raise ValueError("Invalid email format")

                # Convert certifications to list if present
                if 'certifications' in contact_data:
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

            except Exception as e:
                error_count += 1
                error_messages.append(f"Row {index + 2}: {str(e)}")

        # Commit all successful imports
        if success_count > 0:
            db_session.commit()

        return success_count, error_count, error_messages

    except Exception as e:
        logger.error(f"File processing error: {str(e)}")
        return 0, 0, [f"File processing error: {str(e)}"]

def send_email(to_email, subject, body):
    """Send email using SMTP"""
    try:
        # Get email credentials from environment variables
        smtp_server = os.getenv('SMTP_SERVER', 'outlook.office365.com')  # Default to Exchange Online
        smtp_port = int(os.getenv('SMTP_PORT', '587'))  # Default Exchange port
        sender_email = os.getenv('SENDER_EMAIL')
        sender_password = os.getenv('SENDER_PASSWORD')

        if not all([smtp_server, smtp_port, sender_email, sender_password]):
            logger.error("Missing email configuration settings")
            return False

        # Log connection attempt (without sensitive info)
        logger.info(f"Attempting to connect to SMTP server: {smtp_server}:{smtp_port}")

        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        # Add body
        msg.attach(MIMEText(body, 'plain'))

        # Create SMTP session
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()

        logger.info("SMTP connection established, attempting login...")
        try:
            server.login(sender_email, sender_password)
            logger.info("Login successful")
        except smtplib.SMTPAuthenticationError as e:
            logger.error("Authentication failed. If using Exchange Online, ensure you're using the correct password/credentials")
            raise

        # Send email
        server.send_message(msg)
        server.quit()
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}. Please verify your Exchange credentials.")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False