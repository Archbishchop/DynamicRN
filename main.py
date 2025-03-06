import streamlit as st
import pandas as pd
from models import (
    Contact, EmailTemplate, SessionLocal, init_db,
    NURSE_TYPES, NURSING_SPECIALTIES, NURSING_CERTIFICATIONS
)
from utils import validate_email, send_email, process_file_upload
import os
from datetime import datetime

def check_email_configuration():
    """Check if all required email settings are configured"""
    required_settings = ['SMTP_SERVER', 'SMTP_PORT', 'SENDER_EMAIL', 'SENDER_PASSWORD']
    missing_settings = [setting for setting in required_settings if not os.getenv(setting)]

    # For Exchange, suggest default settings if not configured
    if missing_settings:
        if not os.getenv('SMTP_SERVER'):
            st.info("For Microsoft Exchange, try using 'outlook.office365.com' as your SMTP server")
        if not os.getenv('SMTP_PORT'):
            st.info("For Microsoft Exchange, the default SMTP port is 587")

    return len(missing_settings) == 0

# Initialize database
init_db()

# Page configuration
st.set_page_config(
    page_title="Nurse Connect",
    page_icon="👩‍⚕️",
    layout="wide"
)

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = SessionLocal()

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Contacts Management", "Import Contacts", "Email Blast", "Templates"])

# Main header
st.title("Nurse Connect")

if page == "Import Contacts":
    st.header("Import Contacts")

    # File upload
    uploaded_file = st.file_uploader("Upload Contact List", type=['csv', 'xlsx', 'xls'])

    if uploaded_file:
        # Determine file type
        file_type = 'csv' if uploaded_file.name.endswith('.csv') else 'excel'

        # Read and display sample data
        if file_type == 'csv':
            df_sample = pd.read_csv(uploaded_file, nrows=5)
        else:
            df_sample = pd.read_excel(uploaded_file, nrows=5)

        st.write("Preview of first 5 rows:")
        st.write(df_sample)

        # Field mapping
        st.subheader("Map File Columns to Contact Fields")
        st.info("Select which columns from your file correspond to each contact field")

        csv_columns = df_sample.columns.tolist()

        # Create mapping UI
        field_mapping = {}
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Required Fields**")
            field_mapping['first_name'] = st.selectbox(
                "First Name (required)",
                options=[''] + csv_columns
            )
            field_mapping['last_name'] = st.selectbox(
                "Last Name (required)",
                options=[''] + csv_columns
            )
            field_mapping['email'] = st.selectbox(
                "Email (required)",
                options=[''] + csv_columns
            )

        with col2:
            st.write("**Optional Fields**")
            field_mapping['phone_number'] = st.selectbox(
                "Phone Number",
                options=[''] + csv_columns
            )
            field_mapping['nurse_type'] = st.selectbox(
                "Nurse Type",
                options=[''] + csv_columns
            )
            field_mapping['specialty'] = st.selectbox(
                "Specialty",
                options=[''] + csv_columns
            )
            field_mapping['certifications'] = st.selectbox(
                "Certifications (comma-separated)",
                options=[''] + csv_columns
            )
            field_mapping['zip_code'] = st.selectbox(
                "ZIP Code",
                options=[''] + csv_columns
            )
            field_mapping['notes'] = st.selectbox(
                "Notes",
                options=[''] + csv_columns
            )

        # Remove empty mappings
        field_mapping = {k: v for k, v in field_mapping.items() if v}

        if st.button("Import Contacts"):
            if not all([
                field_mapping.get('first_name'),
                field_mapping.get('last_name'),
                field_mapping.get('email')
            ]):
                st.error("Please map all required fields (First Name, Last Name, Email)")
            else:
                # Reset file pointer and read content
                uploaded_file.seek(0)
                file_content = uploaded_file.read()

                # Process import
                with st.spinner("Importing contacts..."):
                    success_count, error_count, error_messages = process_file_upload(
                        file_content,
                        file_type,
                        st.session_state.db,
                        field_mapping
                    )

                # Show results
                st.success(f"Successfully imported {success_count} contacts")
                if error_count > 0:
                    st.warning(f"Failed to import {error_count} contacts")
                    with st.expander("View Error Details"):
                        for error in error_messages:
                            st.write(error)

elif page == "Contacts Management":
    st.header("Contact Management")

    # Add new contact form
    with st.expander("Add New Contact"):
        with st.form("new_contact_form"):
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First Name")
                last_name = st.text_input("Last Name")
                email = st.text_input("Email")
                phone_number = st.text_input("Phone Number")
                nurse_type = st.selectbox("Nurse Type", NURSE_TYPES)
            with col2:
                specialty = st.selectbox("Specialty", NURSING_SPECIALTIES)
                certifications = st.multiselect("Certifications", NURSING_CERTIFICATIONS)
                zip_code = st.text_input("ZIP Code")
                notes = st.text_area("Notes")

            submitted = st.form_submit_button("Add Contact")
            if submitted:
                if not first_name or not last_name or not email:
                    st.error("Please fill in all required fields.")
                elif not validate_email(email):
                    st.error("Please enter a valid email address.")
                else:
                    new_contact = Contact(
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        phone_number=phone_number,
                        nurse_type=nurse_type,
                        specialty=specialty,
                        certifications=certifications,
                        zip_code=zip_code,
                        notes=notes
                    )
                    st.session_state.db.add(new_contact)
                    st.session_state.db.commit()
                    st.success("Contact added successfully!")

    # Contact list with filters
    st.subheader("Contact List")
    col1, col2, col3 = st.columns(3)
    with col1:
        search_term = st.text_input("Search contacts", "")
    with col2:
        nurse_type_filter = st.multiselect(
            "Filter by nurse type",
            options=NURSE_TYPES
        )
    with col3:
        specialty_filter = st.multiselect(
            "Filter by specialty",
            options=NURSING_SPECIALTIES
        )

    # Query contacts
    query = st.session_state.db.query(Contact)
    if search_term:
        query = query.filter(
            (Contact.first_name.ilike(f"%{search_term}%")) |
            (Contact.last_name.ilike(f"%{search_term}%")) |
            (Contact.email.ilike(f"%{search_term}%"))
        )
    if nurse_type_filter:
        query = query.filter(Contact.nurse_type.in_(nurse_type_filter))
    if specialty_filter:
        query = query.filter(Contact.specialty.in_(specialty_filter))

    contacts = query.all()

    # Display contacts in a table format
    if contacts:
        contact_data = []
        for contact in contacts:
            contact_data.append({
                "Name": f"{contact.first_name} {contact.last_name}",
                "Email": contact.email,
                "Phone": contact.phone_number or "N/A",
                "Type": contact.nurse_type,
                "Specialty": contact.specialty,
                "Certifications": ", ".join(contact.certifications) if contact.certifications else "N/A",
                "Actions": contact.id
            })

        df = pd.DataFrame(contact_data)

        # Display the table
        for idx, row in df.iterrows():
            with st.container():
                cols = st.columns([3, 2, 2, 2, 2, 1, 1])
                with cols[0]:
                    st.write(f"**{row['Name']}**")
                with cols[1]:
                    st.write(row['Email'])
                with cols[2]:
                    st.write(row['Phone'])
                with cols[3]:
                    st.write(f"{row['Type']} - {row['Specialty']}")
                with cols[4]:
                    st.write(row['Certifications'])
                with cols[5]:
                    if st.button("📝", key=f"edit_{row['Actions']}"):
                        st.session_state.editing_contact = row['Actions']
                with cols[6]:
                    if st.button("🗑️", key=f"delete_{row['Actions']}"):
                        contact_to_delete = st.session_state.db.query(Contact).get(row['Actions'])
                        if contact_to_delete:
                            st.session_state.db.delete(contact_to_delete)
                            st.session_state.db.commit()
                            st.rerun()
                st.divider()
    else:
        st.info("No contacts found.")

elif page == "Email Blast":
    st.header("Send Email Blast")

    # Check email configuration
    if not check_email_configuration():
        st.error("""
        Email configuration is incomplete. For Microsoft Exchange (Office 365) email:

        1. SMTP Server: outlook.office365.com
        2. SMTP Port: 587
        3. Sender Email: Your work email
        4. Password: Your Office 365 password

        If these settings don't work, please contact your IT department as they may have custom settings.
        """)
        st.stop()

    # Filter contacts
    st.subheader("Select Recipients")
    col1, col2 = st.columns(2)
    with col1:
        specialization_filter = st.multiselect(
            "Filter by specialization",
            options=NURSING_SPECIALTIES
        )
    with col2:
        zip_filter = st.text_input("Filter by ZIP code")

    # Query contacts
    query = st.session_state.db.query(Contact)
    if specialization_filter:
        query = query.filter(Contact.specialty.in_(specialization_filter))
    if zip_filter:
        query = query.filter(Contact.zip_code == zip_filter)

    filtered_contacts = query.all()
    st.write(f"Selected recipients: {len(filtered_contacts)}")

    # Email composition
    st.subheader("Compose Email")
    templates = {t.name: t for t in st.session_state.db.query(EmailTemplate).all()}
    template_name = st.selectbox("Select Template", list(templates.keys()))

    if template_name:
        template = templates[template_name]
        subject = st.text_input("Subject", template.subject)
        body = st.text_area("Body", template.body, height=200)

        if st.button("Send Email Blast"):
            if len(filtered_contacts) == 0:
                st.error("Please select at least one recipient.")
            else:
                progress_bar = st.progress(0)
                for idx, contact in enumerate(filtered_contacts):
                    # Replace placeholders with contact info, using defaults for None values
                    personalized_body = body.replace("[FIRST_NAME]", contact.first_name or "Valued Nurse")
                    personalized_body = personalized_body.replace("[NURSE_TYPE]", contact.nurse_type or "healthcare professional")
                    personalized_body = personalized_body.replace("[SPECIALIZATION]", contact.specialty or "your specialty")

                    success = send_email(
                        to_email=contact.email,
                        subject=subject,
                        body=personalized_body
                    )
                    if success:
                        progress_bar.progress((idx + 1) / len(filtered_contacts))
                st.success(f"Email blast sent to {len(filtered_contacts)} recipients!")

elif page == "Templates":
    st.header("Email Templates")

    # Add new template form
    with st.expander("Add New Template", expanded=False):
        with st.form("new_template_form"):
            template_name = st.text_input("Template Name")
            template_subject = st.text_input("Subject")
            template_body = st.text_area("Body", height=200,
                help="Use [FIRST_NAME] and [SPECIALIZATION] as placeholders")

            if st.form_submit_button("Add Template"):
                if not template_name or not template_subject or not template_body:
                    st.error("Please fill in all fields")
                else:
                    new_template = EmailTemplate(
                        name=template_name,
                        subject=template_subject,
                        body=template_body
                    )
                    st.session_state.db.add(new_template)
                    st.session_state.db.commit()
                    st.success("Template added successfully!")
                    st.rerun()

    # List and manage existing templates
    templates = st.session_state.db.query(EmailTemplate).all()
    for template in templates:
        if template.name != "Network Update":
            with st.expander(f"📧 {template.name}"):
                with st.form(f"edit_template_{template.id}"):
                    edited_name = st.text_input("Template Name", template.name)
                    edited_subject = st.text_input("Subject", template.subject)
                    edited_body = st.text_area("Body", template.body, height=200)

                    col1, col2 = st.columns([1, 4])
                    with col1:
                        if st.form_submit_button("Delete Template"):
                            st.session_state.db.delete(template)
                            st.session_state.db.commit()
                            st.success("Template deleted!")
                            st.rerun()
                    with col2:
                        if st.form_submit_button("Save Changes"):
                            template.name = edited_name
                            template.subject = edited_subject
                            template.body = edited_body
                            st.session_state.db.commit()
                            st.success("Changes saved!")
                            st.rerun()

# Footer
st.markdown("---")
st.markdown("Nurse Connect")

# Cleanup database session
if hasattr(st.session_state, 'db'):
    st.session_state.db.close()