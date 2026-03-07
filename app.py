import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster
from datetime import datetime
from geopy.geocoders import Nominatim

st.set_page_config(page_title="Smart City AI", layout="wide")

# -------------------------
# SESSION STORAGE
# -------------------------

if "complaints" not in st.session_state:
    st.session_state.complaints = []

# -------------------------
# SIDEBAR NAVIGATION
# -------------------------

st.sidebar.title("Smart City AI Dashboard")

page = st.sidebar.radio(
    "Navigation",
    ["Submit Complaint", "Dashboard", "City Map", "Analytics"]
)

# -------------------------
# CLASSIFIER
# -------------------------

def classify_complaint(text):

    text = text.lower()

    if "garbage" in text or "trash" in text:
        return {"Category":"Sanitation","Department":"Waste Management","Urgency":"High"}

    elif "streetlight" in text or "light" in text:
        return {"Category":"Infrastructure","Department":"Electrical Department","Urgency":"Medium"}

    elif "water" in text or "leak" in text:
        return {"Category":"Water Supply","Department":"Water Department","Urgency":"High"}

    elif "traffic" in text or "signal" in text:
        return {"Category":"Traffic","Department":"Traffic Department","Urgency":"Medium"}

    else:
        return {"Category":"General Complaint","Department":"City Services","Urgency":"Low"}

# -------------------------
# REPAIR RECOMMENDATION
# -------------------------

def repair_recommendation(category):

    if category == "Sanitation":
        return "Schedule waste collection and sanitation inspection."

    elif category == "Infrastructure":
        return "Electrical team should inspect and repair the streetlight."

    elif category == "Water Supply":
        return "Water department should inspect and repair the pipeline leakage."

    elif category == "Traffic":
        return "Traffic engineers should inspect and repair the signal."

    else:
        return "City services team should inspect the issue."

# -------------------------
# GEOLOCATION
# -------------------------

def get_coordinates(location):

    try:
        geolocator = Nominatim(user_agent="city_ai_app")
        loc = geolocator.geocode(location)

        if loc:
            return loc.latitude, loc.longitude

    except:
        pass

    return None, None

# -------------------------
# EMAIL REPORT
# -------------------------

def generate_email_report(df):

    total = len(df)
    top_category = df["category"].value_counts().idxmax()

    high = len(df[df["urgency"]=="High"])
    medium = len(df[df["urgency"]=="Medium"])
    low = len(df[df["urgency"]=="Low"])

    resolved = len(df[df["status"]=="Resolved"])
    pending = len(df[df["status"]=="Pending"])

    top_department = df["department"].value_counts().idxmax()

    email = f"""
Subject: Daily City Complaint Report

Dear City Operations Team,

Today the system recorded {total} complaints.

Most common issue: {top_category}

High urgency complaints: {high}
Medium urgency complaints: {medium}
Low urgency complaints: {low}

Resolved complaints: {resolved}
Pending complaints: {pending}

Top department requiring attention: {top_department}

Regards,
Smart City Complaint AI System
"""
    return email

# -------------------------
# SUBMIT COMPLAINT PAGE
# -------------------------

if page == "Submit Complaint":

    st.title("Submit City Complaint")

    with st.form("complaint_form", clear_on_submit=True):

        complaint = st.text_area("Describe the issue")
        location = st.text_input("Location")

        submit = st.form_submit_button("Submit Complaint")

    if submit:

        if complaint.strip()=="":
            st.error("Please enter complaint")

        else:

            result = classify_complaint(complaint)

            lat, lon = get_coordinates(location)

            recommendation = repair_recommendation(result["Category"])

            st.session_state.complaints.append({
                "complaint": complaint,
                "location": location,
                "category": result["Category"],
                "department": result["Department"],
                "urgency": result["Urgency"],
                "recommendation": recommendation,
                "status": "Pending",
                "time": datetime.now(),
                "lat": lat,
                "lon": lon
            })

            st.success("Complaint successfully submitted!")

# -------------------------
# DASHBOARD PAGE
# -------------------------

elif page == "Dashboard":

    st.title("City Complaint Dashboard")

    if len(st.session_state.complaints)==0:
        st.info("No complaints yet")

    else:

        df = pd.DataFrame(st.session_state.complaints)

        high = len(df[df["urgency"]=="High"])
        medium = len(df[df["urgency"]=="Medium"])
        low = len(df[df["urgency"]=="Low"])
        total = len(df)

        c1,c2,c3,c4 = st.columns(4)

        c1.metric("Total Complaints", total)
        c2.metric("High Urgency", high)
        c3.metric("Medium Urgency", medium)
        c4.metric("Low Urgency", low)

        st.subheader("Complaint Table")

        st.dataframe(df)

        st.subheader("Resolve Complaints")

        for i,c in enumerate(st.session_state.complaints):

            if c["status"]=="Pending":

                if st.button(f"Resolve Complaint {i+1}"):

                    st.session_state.complaints[i]["status"]="Resolved"
                    st.rerun()

        st.subheader("Repair Recommendations")

        for c in st.session_state.complaints:

            st.info(f"{c['category']} → {c['recommendation']}")

        st.download_button(
            "Download Complaints CSV",
            df.to_csv(index=False),
            "complaints.csv"
        )

# -------------------------
# MAP PAGE
# -------------------------

elif page == "City Map":

    st.title("City Complaint Map")

    m = folium.Map(location=[20.59,78.96], zoom_start=4)

    cluster = MarkerCluster().add_to(m)

    heat_data=[]

    for c in st.session_state.complaints:

        if c["lat"] and c["lon"]:

            if c["urgency"]=="High":
                color="red"
            elif c["urgency"]=="Medium":
                color="orange"
            else:
                color="green"

            popup=f"""
Location: {c['location']}
Complaint: {c['complaint']}
Department: {c['department']}
Status: {c['status']}
"""

            folium.Marker(
                [c["lat"],c["lon"]],
                popup=popup,
                icon=folium.Icon(color=color)
            ).add_to(cluster)

            heat_data.append([c["lat"],c["lon"]])

    if heat_data:
        HeatMap(heat_data).add_to(m)

    st_folium(m,width=900)

# -------------------------
# ANALYTICS PAGE
# -------------------------

elif page == "Analytics":

    st.title("City Analytics")

    if len(st.session_state.complaints)==0:
        st.info("No analytics yet")

    else:

        df = pd.DataFrame(st.session_state.complaints)

        total=len(df)
        top_category=df["category"].value_counts().idxmax()

        high=len(df[df["urgency"]=="High"])
        medium=len(df[df["urgency"]=="Medium"])
        low=len(df[df["urgency"]=="Low"])

        resolved=len(df[df["status"]=="Resolved"])
        pending=len(df[df["status"]=="Pending"])

        st.subheader("Daily City Report")

        report=f"""
Today the city received {total} complaints.

Most common issue category: {top_category}

High urgency complaints: {high}
Medium urgency complaints: {medium}
Low urgency complaints: {low}

Resolved complaints: {resolved}
Pending complaints: {pending}
"""

        st.info(report)

        st.subheader("Complaint Trend")

        df["time"]=pd.to_datetime(df["time"])
        df["hour"]=df["time"].dt.hour

        trend=df.groupby("hour").size()

        st.line_chart(trend)

        st.subheader("Department Priority")

        dept_counts=df.groupby("department").size().sort_values(ascending=False)

        top_dept=dept_counts.index[0]

        st.success(f"{top_dept} should respond first")

        st.subheader("Generate Authority Email Report")

        if st.button("Generate Email Report"):

            email = generate_email_report(df)

            st.text_area("Email Report", email, height=250)

            st.download_button(
                "Download Email Report",
                email,
                "city_report.txt"
            )