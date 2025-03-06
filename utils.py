import pandas as pd
import smtplib
import os
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_contacts():
    """Load contacts from CSV file or create new dataframe if file doesn't exist"""
    try:
        return pd.read_csv('data/contacts.csv')
    except FileNotFoundError:
        df = pd.DataFrame(columns=['name', 'email', 'specialization', 'zip_code', 'notes'])
        save_contacts(df)
        return df

def save_contacts(df):
    """Save contacts to CSV file"""
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/contacts.csv', index=False)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

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