import streamlit as st

st.title("City Complaint AI Analyzer")

st.header("Submit a Complaint")

complaint = st.text_area("Describe your issue")

location = st.text_input("Location")

if st.button("Submit Complaint"):
    st.success("Complaint submitted successfully!")
    st.write("Complaint:", complaint)
    st.write("Location:", location)