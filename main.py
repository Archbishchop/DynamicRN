import streamlit as st
import pandas as pd
from models import Contact, EmailTemplate, SessionLocal, init_db, NURSE_SPECIALIZATIONS
from utils import validate_email, send_email
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
page = st.sidebar.radio("Go to", ["Contacts Management", "Email Blast", "Templates"])

# Main header
st.title("Nurse Connect")

if page == "Contacts Management":
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
            with col2:
                specialization = st.selectbox("Specialization", NURSE_SPECIALIZATIONS)
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
                        specialization=specialization,
                        zip_code=zip_code,
                        notes=notes
                    )
                    st.session_state.db.add(new_contact)
                    st.session_state.db.commit()
                    st.success("Contact added successfully!")

    # Contact list with filters
    st.subheader("Contact List")
    col1, col2 = st.columns(2)
    with col1:
        search_term = st.text_input("Search contacts", "")
    with col2:
        specialization_filter = st.multiselect(
            "Filter by specialization",
            options=NURSE_SPECIALIZATIONS
        )

    # Query contacts
    query = st.session_state.db.query(Contact)
    if search_term:
        query = query.filter(
            (Contact.first_name.ilike(f"%{search_term}%")) |
            (Contact.last_name.ilike(f"%{search_term}%")) |
            (Contact.email.ilike(f"%{search_term}%"))
        )
    if specialization_filter:
        query = query.filter(Contact.specialization.in_(specialization_filter))

    contacts = query.all()

    # Display contacts in a table format
    if contacts:
        contact_data = []
        for contact in contacts:
            contact_data.append({
                "Name": f"{contact.first_name} {contact.last_name}",
                "Email": contact.email,
                "Phone": contact.phone_number or "N/A",
                "Specialization": contact.specialization,
                "ZIP": contact.zip_code,
                "Actions": contact.id
            })

        df = pd.DataFrame(contact_data)

        # Display the table
        for idx, row in df.iterrows():
            with st.container():
                cols = st.columns([3, 2, 2, 2, 1, 1])
                with cols[0]:
                    st.write(f"**{row['Name']}**")
                with cols[1]:
                    st.write(row['Email'])
                with cols[2]:
                    st.write(row['Phone'])
                with cols[3]:
                    st.write(row['Specialization'])
                with cols[4]:
                    if st.button("📝", key=f"edit_{row['Actions']}"):
                        st.session_state.editing_contact = row['Actions']
                with cols[5]:
                    if st.button("🗑️", key=f"delete_{row['Actions']}"):
                        contact_to_delete = st.session_state.db.query(Contact).get(row['Actions'])
                        if contact_to_delete:
                            st.session_state.db.delete(contact_to_delete)
                            st.session_state.db.commit()
                            st.experimental_rerun()
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
            options=NURSE_SPECIALIZATIONS
        )
    with col2:
        zip_filter = st.text_input("Filter by ZIP code")

    # Query contacts
    query = st.session_state.db.query(Contact)
    if specialization_filter:
        query = query.filter(Contact.specialization.in_(specialization_filter))
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
                    personalized_body = body.replace("[FIRST_NAME]", contact.first_name)
                    personalized_body = personalized_body.replace("[SPECIALIZATION]", contact.specialization)
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
                    st.experimental_rerun()

    # List and manage existing templates
    templates = st.session_state.db.query(EmailTemplate).all()
    for template in templates:
        if template.name != "Network Update":  # Skip the Network Update template
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
                            st.experimental_rerun()
                    with col2:
                        if st.form_submit_button("Save Changes"):
                            template.name = edited_name
                            template.subject = edited_subject
                            template.body = edited_body
                            st.session_state.db.commit()
                            st.success("Changes saved!")
                            st.experimental_rerun()

# Footer
st.markdown("---")
st.markdown("Nurse Connect")

# Cleanup database session
if hasattr(st.session_state, 'db'):
    st.session_state.db.close()