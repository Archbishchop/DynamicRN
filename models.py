from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')
# Log URL safely (hide credentials)
safe_url = DATABASE_URL.replace('://', '://***:***@') if DATABASE_URL else None
logger.info(f"Initializing database with URL: {safe_url}")

# Create database engine
try:
    engine = create_engine(DATABASE_URL)
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone_number = Column(String(20))
    nurse_type = Column(String(50))  # RN, LPN, etc.
    specialty = Column(String(50))    # OR, ER, etc.
    certifications = Column(ARRAY(String))  # Array of certifications
    zip_code = Column(String(10))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    subject = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# List of nurse types
NURSE_TYPES = [
    "Registered Nurse (RN)",
    "Licensed Practical Nurse (LPN)",
    "Certified Nursing Assistant (CNA)",
    "Nurse Practitioner (NP)",
    "Clinical Nurse Specialist (CNS)",
    "Other"
]

# List of nursing specialties
NURSING_SPECIALTIES = [
    "Operating Room",
    "Emergency Room",
    "Intensive Care Unit",
    "Pediatrics",
    "Labor and Delivery",
    "Medical-Surgical",
    "Telemetry",
    "Oncology",
    "Post-Anesthesia Care Unit (PACU)",
    "Psychiatric/Mental Health",
    "Home Health",
    "Case Management",
    "Other"
]

# List of common nursing certifications
NURSING_CERTIFICATIONS = [
    "BLS (Basic Life Support)",
    "ACLS (Advanced Cardiac Life Support)",
    "PALS (Pediatric Advanced Life Support)",
    "NRP (Neonatal Resuscitation Program)",
    "TNCC (Trauma Nursing Core Course)",
    "CCRN (Critical Care RN)",
    "CEN (Certified Emergency Nurse)",
    "CNOR (Certified Nurse Operating Room)",
    "Other"
]

def init_db():
    """Initialize database and create tables"""
    try:
        logger.info("Starting database initialization")

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

        # Inspect database to verify tables
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        logger.info(f"Created tables in database: {table_names}")

        # Initialize session
        db = SessionLocal()
        logger.info("Database session created")

        try:
            # Check if templates already exist
            template_count = db.query(EmailTemplate).count()
            logger.info(f"Found {template_count} existing templates")

            if template_count == 0:
                logger.info("No templates found, creating default templates")
                templates = [
                    EmailTemplate(
                        name="Job Opening",
                        subject="Exciting Nursing Opportunity in Your Area",
                        body="""Dear [FIRST_NAME],

I hope this email finds you well. I wanted to reach out about an exciting nursing opportunity that matches your expertise as a [NURSE_TYPE] in [SPECIALTY].

We are currently seeking experienced nurses for a prestigious healthcare facility in your area.

Would you be interested in learning more about this opportunity? If so, please reply to this email or call me directly.

Best regards,
[Your Name]
Nurse Recruiter"""
                    ),
                    EmailTemplate(
                        name="Follow Up",
                        subject="Following Up - Nursing Position",
                        body="""Dear [FIRST_NAME],

I wanted to follow up regarding the nursing position we discussed previously. Have you had a chance to consider the opportunity?

I'm available to answer any questions you might have about the role or the facility.

Looking forward to hearing from you.

Best regards,
[Your Name]
Nurse Recruiter"""
                    )
                ]
                db.add_all(templates)
                db.commit()
                logger.info("Default templates created successfully")
        finally:
            db.close()
            logger.info("Database session closed")

        return True
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return False

# Initialize the database
logger.info("Starting database initialization process")
init_db()
logger.info("Database initialization completed")