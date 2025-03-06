import streamlit as st
import pandas as pd
from models import (
    Contact, EmailTemplate, SessionLocal, init_db,
    NURSE_TYPES, NURSING_SPECIALTIES, NURSING_CERTIFICATIONS
)
from utils import validate_email, send_email, process_file_upload, verify_smtp_connection
import os
from datetime import datetime

def check_email_configuration():
    """Check if all required email settings are configured"""
    required_settings = ['SMTP_SERVER', 'SMTP_PORT', 'SENDER_EMAIL', 'SENDER_PASSWORD']
    missing_settings = [setting for setting in required_settings if not os.getenv(setting)]

    # For Exchange, suggest default settings if not configured
    error_message = ""
    if not os.getenv('SMTP_SERVER'):
        error_message += "SMTP Server not configured. For Microsoft Exchange, try 'outlook.office365.com'.\n"
    if not os.getenv('SMTP_PORT'):
        error_message += "SMTP Port not configured. For Microsoft Exchange, the default is 587.\n"
    if not os.getenv('SENDER_EMAIL'):
        error_message += "Sender Email not configured.\n"
    if not os.getenv('SENDER_PASSWORD'):
        error_message += "Sender Password not configured.\n"

    return len(missing_settings) == 0, error_message

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
if 'editing_contact' not in st.session_state:
    st.session_state.editing_contact = None

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Contacts Management", "Import Contacts", "Email Blast", "Templates"])

# Main header
st.markdown("<h1 style='text-align: center;'>Nurse Connect</h1>", unsafe_allow_html=True)

if page == "Import Contacts":
    st.header("Import Contacts")

    # File upload
    uploaded_file = st.file_uploader("Upload Contact List", type=['csv', 'xlsx', 'xls'])

    if uploaded_file:
        # Determine file type
        file_type = 'csv' if uploaded_file.name.endswith('.csv') else 'excel'

        try:
            # Read and display sample data
            if file_type == 'csv':
                df_sample = pd.read_csv(uploaded_file, nrows=5)
            else:
                df_sample = pd.read_excel(uploaded_file, nrows=5)

            st.write("Preview of first 5 rows:")
            st.write(df_sample)

            # Display available columns
            st.write("Available columns in file:", ", ".join(df_sample.columns.tolist()))

            # Field mapping
            st.subheader("Map File Columns to Contact Fields")
            st.info("Select which columns from your file correspond to each contact field")

            csv_columns = df_sample.columns.tolist()

            # Create mapping UI
            with st.form("field_mapping_form"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Required Fields**")
                    field_mapping = {}
                    field_mapping['first_name'] = st.selectbox(
                        "First Name (required)",
                        options=[''] + csv_columns,
                        help="Select the column containing first names"
                    )
                    field_mapping['last_name'] = st.selectbox(
                        "Last Name (required)",
                        options=[''] + csv_columns,
                        help="Select the column containing last names"
                    )
                    field_mapping['email'] = st.selectbox(
                        "Email (required)",
                        options=[''] + csv_columns,
                        help="Select the column containing email addresses"
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

                submitted = st.form_submit_button("Import Contacts")

                if submitted:
                    # Remove empty mappings
                    field_mapping = {k: v for k, v in field_mapping.items() if v}

                    if not all([
                        field_mapping.get('first_name'),
                        field_mapping.get('last_name'),
                        field_mapping.get('email')
                    ]):
                        st.error("Please map all required fields (First Name, Last Name, Email)")
                    else:
                        # Show selected mappings
                        st.write("Selected field mappings:")
                        for field, column in field_mapping.items():
                            st.write(f"- {field}: {column}")

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
                        if success_count > 0:
                            st.success(f"Successfully imported {success_count} contacts")
                        else:
                            st.warning("No contacts were imported. Please check the error details below.")

                        if error_count > 0:
                            st.error(f"Failed to import {error_count} contacts")
                            with st.expander("View Error Details"):
                                for error in error_messages:
                                    st.write(error)

        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
            st.write("Please ensure your file is properly formatted and try again.")

elif page == "Contacts Management":
    st.markdown("<h2 style='text-align: center;'>Contact Management</h2>", unsafe_allow_html=True)

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

    # Contact list and editing interface
    st.subheader("Contact List")

    # Filters section in 2x2 grid
    st.write("### Filter Contacts")
    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)

    with row1_col1:
        search_term = st.text_input("Search contacts", "")
    with row1_col2:
        nurse_type_filter = st.multiselect(
            "Filter by nurse type",
            options=NURSE_TYPES
        )
    with row2_col1:
        specialty_filter = st.multiselect(
            "Filter by specialty",
            options=NURSING_SPECIALTIES
        )
    with row2_col2:
        zip_filter = st.text_input("Filter by ZIP code")

    # Query contacts with filters
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

    # Get total count for pagination
    total_contacts = query.count()
    contacts_per_page = 20
    total_pages = (total_contacts + contacts_per_page - 1) // contacts_per_page

    # Pagination controls
    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        current_page = st.selectbox(
            "Page",
            options=range(1, total_pages + 1),
            format_func=lambda x: f"Page {x} of {total_pages}"
        ) if total_pages > 0 else 1

    # Get paginated contacts
    offset = (current_page - 1) * contacts_per_page
    contacts = query.offset(offset).limit(contacts_per_page).all()

    # Initialize session state for selected contacts if not exists
    if 'selected_contacts' not in st.session_state:
        st.session_state.selected_contacts = set()
    if 'show_delete_confirmation' not in st.session_state:
        st.session_state.show_delete_confirmation = False

    # Bulk Actions Section
    st.subheader("Bulk Actions")
    selected_count = len(st.session_state.selected_contacts)

    # Function to handle selection changes
    def update_selection(contact_id, is_selected):
        if is_selected:
            st.session_state.selected_contacts.add(contact_id)
        else:
            st.session_state.selected_contacts.discard(contact_id)
        st.rerun()

    if selected_count > 0:
        st.write(f"{selected_count} contacts selected")

        if not st.session_state.show_delete_confirmation:
            if st.button("Delete Selected", type="secondary"):
                st.session_state.show_delete_confirmation = True
                st.rerun()
        else:
            st.warning(f"Are you sure you want to delete {selected_count} contacts?")
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("✓ Confirm", type="primary"):
                    try:
                        # Delete selected contacts
                        deleted_count = 0
                        for contact_id in list(st.session_state.selected_contacts):  # Convert to list to avoid modification during iteration
                            contact = st.session_state.db.query(Contact).get(contact_id)
                            if contact:
                                st.session_state.db.delete(contact)
                                deleted_count += 1

                        # Commit changes
                        st.session_state.db.commit()

                        # Reset states
                        st.session_state.selected_contacts = set()
                        st.session_state.show_delete_confirmation = False

                        st.success(f"Successfully deleted {deleted_count} contacts!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting contacts: {str(e)}")
                        st.session_state.db.rollback()
            with col2:
                if st.button("✗ Cancel", type="secondary"):
                    st.session_state.show_delete_confirmation = False
                    st.rerun()

    st.divider()

    # Display contacts with checkboxes
    if contacts:
        for contact in contacts:
            with st.container():
                cols = st.columns([0.5, 2.5, 2, 2, 2, 2, 0.5, 0.5])

                # Selection checkbox
                with cols[0]:
                    checkbox_state = st.checkbox(
                        "",
                        key=f"select_{contact.id}",
                        value=contact.id in st.session_state.selected_contacts,
                        label_visibility="collapsed",
                        on_change=update_selection,
                        args=(contact.id, not (contact.id in st.session_state.selected_contacts))
                    )

                # Contact information
                with cols[1]:
                    st.write(f"**{contact.first_name} {contact.last_name}**")
                with cols[2]:
                    st.write(contact.email)
                with cols[3]:
                    st.write(contact.phone_number or "N/A")
                with cols[4]:
                    nurse_type_display = contact.nurse_type
                    if contact.nurse_type and '(' in contact.nurse_type:
                        nurse_type_display = contact.nurse_type.split('(')[1].rstrip(')')
                    st.write(f"{nurse_type_display} - {contact.specialty}")
                with cols[5]:
                    cert_acronyms = []
                    if contact.certifications:
                        for cert in contact.certifications:
                            if '(' in cert:
                                acronym = cert.split('(')[0].strip()
                                cert_acronyms.append(acronym)
                            else:
                                cert_acronyms.append(cert)
                    st.write(", ".join(cert_acronyms) if cert_acronyms else "N/A")

                # Action buttons
                with cols[6]:
                    if st.button("📝", key=f"edit_{contact.id}"):
                        st.session_state.editing_contact = contact.id
                        st.rerun()
                with cols[7]:
                    if st.button("🗑️", key=f"delete_{contact.id}"):
                        contact_to_delete = st.session_state.db.query(Contact).get(contact.id)
                        if contact_to_delete:
                            st.session_state.db.delete(contact_to_delete)
                            st.session_state.db.commit()
                            st.success(f"Deleted contact: {contact.first_name} {contact.last_name}")
                            st.rerun()
                st.divider()
    else:
        st.info("No contacts found.")

    # Edit contact form
    if st.session_state.editing_contact:
        st.subheader("Edit Contact")
        contact = st.session_state.db.query(Contact).get(st.session_state.editing_contact)
        if contact:
            with st.form("edit_contact_form"):
                col1, col2 = st.columns(2)
                with col1:
                    edited_first_name = st.text_input("First Name", contact.first_name)
                    edited_last_name = st.text_input("Last Name", contact.last_name)
                    edited_email = st.text_input("Email", contact.email)
                    edited_phone_number = st.text_input("Phone Number", contact.phone_number or "")
                    edited_nurse_type = st.selectbox("Nurse Type", NURSE_TYPES,
                        index=NURSE_TYPES.index(contact.nurse_type) if contact.nurse_type in NURSE_TYPES else 0)
                with col2:
                    edited_specialty = st.selectbox("Specialty", NURSING_SPECIALTIES,
                        index=NURSING_SPECIALTIES.index(contact.specialty) if contact.specialty in NURSING_SPECIALTIES else 0)
                    default_certs = [cert for cert in contact.certifications if cert in NURSING_CERTIFICATIONS] if contact.certifications else []
                    edited_certifications = st.multiselect("Certifications", NURSING_CERTIFICATIONS,
                        default=default_certs)
                    edited_zip_code = st.text_input("ZIP Code", contact.zip_code or "")
                    edited_notes = st.text_area("Notes", contact.notes or "")

                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.form_submit_button("Cancel"):
                        st.session_state.editing_contact = None
                        st.rerun()
                with col2:
                    if st.form_submit_button("Save Changes"):
                        if not edited_first_name or not edited_last_name or not edited_email:
                            st.error("Please fill in all required fields.")
                        elif not validate_email(edited_email):
                            st.error("Please enter a valid email address.")
                        else:
                            contact.first_name = edited_first_name
                            contact.last_name = edited_last_name
                            contact.email = edited_email
                            contact.phone_number = edited_phone_number
                            contact.nurse_type = edited_nurse_type
                            contact.specialty = edited_specialty
                            contact.certifications = edited_certifications
                            contact.zip_code = edited_zip_code
                            contact.notes = edited_notes
                            st.session_state.db.commit()
                            st.success("Contact updated successfully!")
                            st.session_state.editing_contact = None
                            st.rerun()

elif page == "Email Blast":
    st.header("Send Email Blast")

    # Email Configuration Section
    with st.expander("✉️ Email Settings", expanded=True):
        st.subheader("Office 365 Email Configuration")

        col1, col2 = st.columns(2)
        with col1:
            st.info("""
            Configure your email account:
            1. Enter your work email (Office 365 or other email)
            2. For Office 365 with MFA, use an App Password:
               - Go to Office 365 Account Settings
               - Security → App Passwords
               - Create a new App Password

            Note: Each user can configure their own email account.
            Settings are per-session and will need to be re-entered 
            when you restart the application.
            """)

            # Email configuration form
            with st.form("email_settings"):
                email = st.text_input("Email Address")
                password = st.text_input("Password or App Password", type="password",
                    help="For Office 365 with MFA, use an App Password")

                if st.form_submit_button("Save Email Settings"):
                    if email and password:
                        os.environ['SENDER_EMAIL'] = email
                        os.environ['SENDER_PASSWORD'] = password
                        st.success("✅ Email settings updated!")
                    else:
                        st.error("Please enter both email and password.")

        with col2:
            st.write("Current Configuration:")
            st.write(f"- SMTP Server: outlook.office365.com")
            st.write(f"- SMTP Port: 587")
            st.write(f"- Email: {os.getenv('SENDER_EMAIL', 'Not configured')}")

            if st.button("Test Connection"):
                with st.spinner("Testing email connection..."):
                    connection_ok, connection_error = verify_smtp_connection()
                    if connection_ok:
                        st.success("✅ Successfully connected!")
                    else:
                        st.error(f"❌ Connection failed: {connection_error}")

    # Check if email is configured before allowing email blast
    config_ok, config_error = check_email_configuration()
    if not config_ok:
        st.error("Please configure your email settings above before sending email blasts.")
        st.stop()

    # Filter contacts
    st.subheader("Select Recipients")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        nurse_type_filter = st.multiselect(
            "Filter by nurse type",
            options=NURSE_TYPES
        )
    with col2:
        specialty_filter = st.multiselect(
            "Filter by specialty",
            options=NURSING_SPECIALTIES
        )
    with col3:
        certification_filter = st.multiselect(
            "Filter by certification",
            options=NURSING_CERTIFICATIONS
        )
    with col4:
        zip_filter = st.text_input("Filter by ZIP code")

    # Query contacts
    query = st.session_state.db.query(Contact)
    if nurse_type_filter:
        query = query.filter(Contact.nurse_type.in_(nurse_type_filter))
    if specialty_filter:
        query = query.filter(Contact.specialty.in_(specialty_filter))
    if certification_filter:
        # Filter contacts that have any of the selected certifications
        query = query.filter(Contact.certifications.overlap(certification_filter))
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
                # Test connection before sending
                connection_ok, connection_error = verify_smtp_connection()
                if not connection_ok:
                    st.error(f"Email configuration error: {connection_error}")
                    st.stop()

                progress_container = st.container()
                with progress_container:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    error_container = st.container()

                    success_count = 0
                    error_count = 0
                    error_messages = []

                    for idx, contact in enumerate(filtered_contacts):
                        status_text.write(f"Sending email to {contact.email}...")

                        # Replace placeholders with contact info
                        personalized_body = body.replace("[FIRST_NAME]", contact.first_name or "Valued Nurse")
                        personalized_body = personalized_body.replace("[NURSE_TYPE]", contact.nurse_type or "healthcare professional")
                        personalized_body = personalized_body.replace("[SPECIALTY]", contact.specialty or "your specialty")

                        success, error_msg = send_email(
                            to_email=contact.email,
                            subject=subject,
                            body=personalized_body
                        )

                        if success:
                            success_count += 1
                        else:
                            error_count += 1
                            error_messages.append(f"Failed to send email to {contact.email}: {error_msg}")

                        progress_bar.progress((idx + 1) / len(filtered_contacts))

                    # Show final results
                    if success_count > 0:
                        st.success(f"✅ Successfully sent {success_count} emails")
                    if error_count > 0:
                        with error_container:
                            st.error(f"❌ Failed to send {error_count} emails")
                            with st.expander("View Error Details"):
                                for error in error_messages:
                                    st.write(error)

elif page == "Templates":
    st.header("Email Templates")

    # Add new template form
    with st.expander("Add New Template", expanded=False):
        with st.form("new_template_form"):
            template_name = st.text_input("Template Name")
            template_subject = st.text_input("Subject")
            template_body = st.text_area("Body", height=200,
                help="Use [FIRST_NAME], [NURSE_TYPE], and [SPECIALTY] as placeholders")

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

def ask_secrets(secret_keys, user_message):
    for key in secret_keys:
        new_value = st.text_input(f"Enter new value for {key}:", type="password")
        if new_value:
            os.environ[key] = new_value
            st.success(f"{key} updated successfully!")
        else:
            st.warning(f"No value provided for {key}.")