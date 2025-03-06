import streamlit as st
import pandas as pd
from utils import load_contacts, save_contacts, send_email, validate_email
from email_templates import templates
import os

# Page configuration
st.set_page_config(
    page_title="Healthcare Recruiter Email System",
    page_icon="💊",
    layout="wide"
)

# Initialize session state
if 'contacts_df' not in st.session_state:
    st.session_state.contacts_df = load_contacts()

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
                    new_contact = pd.DataFrame([[name, email, specialization, zip_code, notes]], 
                        columns=['name', 'email', 'specialization', 'zip_code', 'notes'])
                    st.session_state.contacts_df = pd.concat([st.session_state.contacts_df, new_contact], 
                        ignore_index=True)
                    save_contacts(st.session_state.contacts_df)
                    st.success("Contact added successfully!")

    # Contact list with filters
    st.subheader("Contact List")
    col1, col2 = st.columns(2)
    with col1:
        search_term = st.text_input("Search contacts", "")
    with col2:
        specialization_filter = st.multiselect(
            "Filter by specialization",
            options=st.session_state.contacts_df['specialization'].unique()
        )

    filtered_df = st.session_state.contacts_df
    if search_term:
        filtered_df = filtered_df[
            filtered_df['name'].str.contains(search_term, case=False) |
            filtered_df['email'].str.contains(search_term, case=False)
        ]
    if specialization_filter:
        filtered_df = filtered_df[filtered_df['specialization'].isin(specialization_filter)]

    # Display contacts with edit/delete buttons
    for idx, row in filtered_df.iterrows():
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"**{row['name']}** ({row['specialization']})")
            st.write(f"Email: {row['email']} | ZIP: {row['zip_code']}")
        with col2:
            if st.button("Edit", key=f"edit_{idx}"):
                st.session_state.editing_idx = idx
        with col3:
            if st.button("Delete", key=f"delete_{idx}"):
                st.session_state.contacts_df = st.session_state.contacts_df.drop(idx)
                save_contacts(st.session_state.contacts_df)
                st.experimental_rerun()

elif page == "Email Blast":
    st.header("Send Email Blast")
    
    # Filter contacts
    st.subheader("Select Recipients")
    col1, col2 = st.columns(2)
    with col1:
        specialization_filter = st.multiselect(
            "Filter by specialization",
            options=st.session_state.contacts_df['specialization'].unique()
        )
    with col2:
        zip_filter = st.text_input("Filter by ZIP code")

    filtered_df = st.session_state.contacts_df
    if specialization_filter:
        filtered_df = filtered_df[filtered_df['specialization'].isin(specialization_filter)]
    if zip_filter:
        filtered_df = filtered_df[filtered_df['zip_code'] == zip_filter]

    st.write(f"Selected recipients: {len(filtered_df)}")
    
    # Email composition
    st.subheader("Compose Email")
    template = st.selectbox("Select Template", list(templates.keys()))
    subject = st.text_input("Subject", templates[template]["subject"])
    body = st.text_area("Body", templates[template]["body"], height=200)
    
    if st.button("Send Email Blast"):
        if len(filtered_df) == 0:
            st.error("Please select at least one recipient.")
        else:
            progress_bar = st.progress(0)
            for idx, row in filtered_df.iterrows():
                personalized_body = body.replace("[NAME]", row['name'])
                success = send_email(
                    to_email=row['email'],
                    subject=subject,
                    body=personalized_body
                )
                if success:
                    progress_bar.progress((idx + 1) / len(filtered_df))
            st.success(f"Email blast sent to {len(filtered_df)} recipients!")

elif page == "Templates":
    st.header("Email Templates")
    
    for template_name, template_content in templates.items():
        with st.expander(template_name):
            st.write("**Subject:**", template_content["subject"])
            st.write("**Body:**", template_content["body"])

# Footer
st.markdown("---")
st.markdown("Healthcare Recruiter Email System - Made with ❤️ by Your Team")
