import pandas as pd
import smtplib
import os
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL', 'your-email@example.com')
        sender_password = os.getenv('SENDER_PASSWORD', 'your-password')

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
        server.login(sender_email, sender_password)
        
        # Send email
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False
