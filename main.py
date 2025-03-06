import streamlit as st
import pandas as pd
from models import Contact, EmailTemplate, SessionLocal, init_db
from utils import validate_email, send_email
import os
from datetime import datetime

# Initialize database
init_db()

# Page configuration
st.set_page_config(
    page_title="Healthcare Recruiter Email System",
    page_icon="💊",
    layout="wide"
)

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = SessionLocal()

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Contacts Management", "Email Blast", "Templates"])

# Main header
st.title("Healthcare Recruiter Email System")

if page == "Contacts Management":
    st.header("Contact Management")

    # Add new contact form
    with st.expander("Add New Contact"):
        with st.form("new_contact_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name")
                email = st.text_input("Email")
                specialization = st.selectbox("Specialization", 
                    ["Nurse", "Doctor", "Surgeon", "Specialist", "Administrator", "Other"])
            with col2:
                zip_code = st.text_input("ZIP Code")
                notes = st.text_area("Notes")

            submitted = st.form_submit_button("Add Contact")
            if submitted:
                if not name or not email or not zip_code:
                    st.error("Please fill in all required fields.")
                elif not validate_email(email):
                    st.error("Please enter a valid email address.")
                else:
                    new_contact = Contact(
                        name=name,
                        email=email,
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
        specializations = [spec[0] for spec in st.session_state.db.query(Contact.specialization).distinct()]
        specialization_filter = st.multiselect(
            "Filter by specialization",
            options=specializations
        )

    # Query contacts
    query = st.session_state.db.query(Contact)
    if search_term:
        query = query.filter(
            (Contact.name.ilike(f"%{search_term}%")) |
            (Contact.email.ilike(f"%{search_term}%"))
        )
    if specialization_filter:
        query = query.filter(Contact.specialization.in_(specialization_filter))

    contacts = query.all()

    # Display contacts with edit/delete buttons
    for contact in contacts:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"**{contact.name}** ({contact.specialization})")
            st.write(f"Email: {contact.email} | ZIP: {contact.zip_code}")
        with col2:
            if st.button("Edit", key=f"edit_{contact.id}"):
                st.session_state.editing_contact = contact.id
        with col3:
            if st.button("Delete", key=f"delete_{contact.id}"):
                st.session_state.db.delete(contact)
                st.session_state.db.commit()
                st.experimental_rerun()

elif page == "Email Blast":
    st.header("Send Email Blast")

    # Filter contacts
    st.subheader("Select Recipients")
    col1, col2 = st.columns(2)
    with col1:
        specializations = [spec[0] for spec in st.session_state.db.query(Contact.specialization).distinct()]
        specialization_filter = st.multiselect(
            "Filter by specialization",
            options=specializations
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
                    personalized_body = body.replace("[NAME]", contact.name)
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

    templates = st.session_state.db.query(EmailTemplate).all()
    for template in templates:
        with st.expander(template.name):
            st.write("**Subject:**", template.subject)
            st.write("**Body:**", template.body)

# Footer
st.markdown("---")
st.markdown("Healthcare Recruiter Email System - Made with ❤️ by Your Team")

# Cleanup database session
if hasattr(st.session_state, 'db'):
    st.session_state.db.close()