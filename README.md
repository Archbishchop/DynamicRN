# Nurse Connect

A healthcare recruitment management system designed to streamline communication and candidate tracking for nursing professionals.

## Project Structure
```
nurse-connect/
├── data/
│   └── contacts.csv
├── main.py
├── models.py
├── utils.py
├── email_templates.py
├── pyproject.toml
└── README.md
```

## Features
- Contact management with advanced filtering
- Bulk contact operations
- Email blast functionality with Microsoft Exchange integration
- Template-based email communications
- Certification-based filtering
- Multi-user support

## Prerequisites
- Python 3.11+
- PostgreSQL database
- SMTP server access (Microsoft Exchange)

## Required Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@host:port/dbname

# Email Configuration (Microsoft Exchange)
SMTP_SERVER=outlook.office365.com
SMTP_PORT=587
SENDER_EMAIL=your-email@domain.com
SENDER_PASSWORD=your-app-password
```

Note: For Office 365 with MFA enabled, you'll need to use an App Password instead of your regular password.

## Installation Steps

1. Create and activate a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install required packages from pyproject.toml:
```bash
pip install openpyxl==3.1.5
pip install pandas==2.2.3
pip install psycopg2-binary==2.9.10
pip install sqlalchemy==2.0.38
pip install streamlit==1.43.0
pip install twilio==9.4.6
```

3. Set up your PostgreSQL database and update the DATABASE_URL environment variable

4. Configure your email settings in environment variables

## Running the Application

1. Start the Streamlit application:
```bash
streamlit run main.py
```

The application will be available at `http://localhost:5000`

## Database Schema

The application uses two main tables:
1. contacts - Stores nurse contact information
2. email_templates - Stores email templates for communication

## Features Usage

### Contact Management
- Add/Edit/Delete individual contacts
- Bulk import contacts via CSV/Excel
- Bulk delete selected contacts
- Filter contacts by nurse type, specialty, certification

### Email System
- Configure email settings for Office 365
- Create and manage email templates
- Send bulk emails with personalized content
- Filter recipients by various criteria

## Downloading from Replit
1. In the Replit interface, locate each file in the file explorer
2. Click on each file to open it
3. Use the "Copy" button or download option for each file
4. Save the files in your local project directory following the structure shown above

## Support
For any issues or questions, please refer to the documentation or contact your system administrator.