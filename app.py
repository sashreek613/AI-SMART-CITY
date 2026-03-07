import streamlit as st
import pandas as pd
import folium
import uuid
import requests
from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster
from datetime import datetime
from geopy.geocoders import Nominatim
from textblob import TextBlob
from streamlit_js_eval import get_geolocation
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Smart City AI Command Center", layout="wide")

# AUTO REFRESH
st_autorefresh(interval=10000, key="refresh")

geolocator = Nominatim(user_agent="smart_city_ai")

# SESSION STORAGE
if "complaints" not in st.session_state:
    st.session_state.complaints = []

# LOAD CITY DATA
@st.cache_data(ttl=300)
def load_city_data():

    url = "https://data.montgomeryal.gov/resource/8u7v-jw6c.json"

    try:
        r = requests.get(url)
        data = r.json()
        df = pd.DataFrame(data)

        if "latitude" in df.columns:
            df["lat"] = pd.to_numeric(df["latitude"], errors="coerce")
            df["lon"] = pd.to_numeric(df["longitude"], errors="coerce")

        return df

    except:
        return pd.DataFrame()

city_df = load_city_data()

# AI SUMMARY
def summarize(text):

    blob = TextBlob(text)

    if len(blob.sentences) > 0:
        return str(blob.sentences[0])

    return text[:80]

# URGENCY DETECTION
def detect_urgency(text):

    text = text.lower()

    high_keywords = ["fire","accident","sewage","leak"]
    medium_keywords = ["traffic","pothole","garbage"]

    score = 0

    for w in high_keywords:
        if w in text:
            score += 3

    for w in medium_keywords:
        if w in text:
            score += 2

    if score >= 5:
        return "High"
    elif score >= 3:
        return "Medium"
    else:
        return "Low"

# CLASSIFIER
def classify(text):

    text = text.lower()

    if "garbage" in text:
        return "Sanitation","Waste Management"

    elif "light" in text:
        return "Infrastructure","Electrical"

    elif "water" in text:
        return "Water","Water Department"

    elif "traffic" in text:
        return "Traffic","Traffic Department"

    elif "pothole" in text:
        return "Road Damage","Road Department"

    return "General","City Services"

# GEO FUNCTIONS
def get_coordinates(location):

    try:
        loc = geolocator.geocode(location)

        if loc:
            return loc.latitude, loc.longitude, loc.address

    except:
        pass

    return None,None,location


def reverse_geocode(lat,lon):

    try:
        loc = geolocator.reverse((lat,lon))

        if loc:
            return loc.address

    except:
        pass

    return f"{lat},{lon}"

# SIDEBAR
st.sidebar.title("Smart City System")

page = st.sidebar.radio(
    "Navigation",
    [
        "Citizen Portal",
        "Track Complaint",
        "Government Portal",
        "Dashboard",
        "City Map",
        "Analytics",
        "Risk Dashboard",
        "Emergency Alerts"
    ]
)

# CITIZEN PORTAL
if page == "Citizen Portal":

    st.title("Citizen Complaint Portal")

    if st.button("📍 Use Current Location"):

        gps = get_geolocation()

        if gps:
            st.session_state.lat = gps["coords"]["latitude"]
            st.session_state.lon = gps["coords"]["longitude"]
            st.session_state.address = reverse_geocode(
                st.session_state.lat,
                st.session_state.lon
            )

            st.success(f"Location detected: {st.session_state.address}")

    with st.form("complaint_form", clear_on_submit=True):

        complaint = st.text_area("Describe Issue")

        location = st.text_input("Enter Location")

        image = st.file_uploader("Upload Photo", type=["jpg","png","jpeg"])

        if image:
            st.image(image, caption="Uploaded Issue Photo", width=300)

        lat = None
        lon = None
        address = location

        if location:
            lat,lon,address = get_coordinates(location)

        if "lat" in st.session_state:
            lat = st.session_state.lat
            lon = st.session_state.lon
            address = st.session_state.address

        st.subheader("Select location on map")

        map_select = folium.Map(location=[32.37,-86.30],zoom_start=12)

        map_data = st_folium(map_select,height=400)

        if map_data and map_data["last_clicked"]:
            lat = map_data["last_clicked"]["lat"]
            lon = map_data["last_clicked"]["lng"]
            address = reverse_geocode(lat,lon)

        submitted = st.form_submit_button("Submit Complaint")

        if submitted:

            if complaint.strip() == "":
                st.error("Please describe the issue")
                st.stop()

            summary = summarize(complaint)
            urgency = detect_urgency(complaint)
            category,department = classify(complaint)

            complaint_id = str(uuid.uuid4())[:8]

            st.session_state.complaints.append({

                "id":complaint_id,
                "complaint":complaint,
                "summary":summary,
                "location":address,
                "category":category,
                "department":department,
                "urgency":urgency,
                "lat":lat,
                "lon":lon,
                "image":image,
                "status":"Pending",
                "time":datetime.now()

            })

            st.success(f"Complaint Submitted. Your ID: {complaint_id}")

# TRACK COMPLAINT
elif page == "Track Complaint":

    st.title("Track Complaint")

    cid = st.text_input("Enter Complaint ID")

    if st.button("Track"):

        df = pd.DataFrame(st.session_state.complaints)

        result = df[df["id"]==cid]

        if len(result)==0:
            st.error("Complaint not found")

        else:

            row = result.iloc[0]

            st.write("Issue:",row["summary"])
            st.write("Location:",row["location"])
            st.write("Department:",row["department"])

            status=row["status"]

            if status=="Pending":
                st.info("Complaint received")

            elif status=="In Progress":
                st.warning("Work in progress")

            elif status=="Resolved":
                st.success("Issue resolved")

# GOVERNMENT PORTAL
elif page == "Government Portal":

    st.title("Government Control Panel")

    df=pd.DataFrame(st.session_state.complaints)

    if len(df)==0:
        st.info("No complaints")

    else:

        priority_map = {"High":3,"Medium":2,"Low":1}
        df["priority"] = df["urgency"].map(priority_map)
        df = df.sort_values("priority", ascending=False)

        for i,row in df.iterrows():

            st.write("Issue:",row["summary"])
            st.write("Location:",row["location"])
            st.write("Urgency:",row["urgency"])

            if row["image"]:
                st.image(row["image"], width=250)

            status=st.selectbox(
                "Update Status",
                ["Pending","In Progress","Resolved"],
                index=["Pending","In Progress","Resolved"].index(row["status"]),
                key=f"s{i}"
            )

            if st.button("Update",key=f"b{i}"):

                st.session_state.complaints[i]["status"]=status
                st.success("Updated")

            st.divider()

# DASHBOARD
elif page=="Dashboard":

    st.title("City Dashboard")

    df=pd.DataFrame(st.session_state.complaints)

    if len(df)==0:
        st.info("No complaints")

    else:

        c1,c2,c3=st.columns(3)

        c1.metric("Total",len(df))
        c2.metric("High",len(df[df["urgency"]=="High"]))
        c3.metric("Resolved",len(df[df["status"]=="Resolved"]))

        st.dataframe(df[["id","summary","location","department","urgency","status"]])

        st.download_button(
            "Download Complaints CSV",
            df.to_csv(index=False),
            "complaints.csv"
        )

# CITY MAP
elif page=="City Map":

    st.title("City Issue Map")

    m=folium.Map(location=[32.37,-86.30],zoom_start=12)

    cluster=MarkerCluster().add_to(m)

    heat=[]

    df=pd.DataFrame(st.session_state.complaints)

    for _,row in df.iterrows():

        if pd.notnull(row["lat"]):

            folium.Marker(
                [row["lat"],row["lon"]],
                popup=row["summary"],
                icon=folium.Icon(color="red")
            ).add_to(cluster)

            heat.append([row["lat"],row["lon"]])

    for _,row in city_df.iterrows():

        if "lat" in row and pd.notnull(row["lat"]):

            folium.Marker(
                [row["lat"],row["lon"]],
                popup="City Data",
                icon=folium.Icon(color="blue")
            ).add_to(cluster)

            heat.append([row["lat"],row["lon"]])

    if heat:
        HeatMap(heat).add_to(m)

    st_folium(m,width=900,height=600)

# ANALYTICS
elif page=="Analytics":

    st.title("City Analytics")

    df=pd.DataFrame(st.session_state.complaints)

    if len(df)>0:

        st.bar_chart(df["department"].value_counts())
        st.bar_chart(df["location"].value_counts())

# RISK DASHBOARD
elif page=="Risk Dashboard":

    st.title("City Risk Prediction")

    df=pd.DataFrame(st.session_state.complaints)

    if len(df)==0:
        st.info("No data")

    else:

        risk=df["urgency"].map({
            "High":5,
            "Medium":3,
            "Low":1
        }).sum()

        if risk<10:
            level="Low"
        elif risk<25:
            level="Moderate"
        elif risk<50:
            level="High"
        else:
            level="Critical"

        st.metric("City Risk Level",level)

# EMERGENCY ALERTS
elif page=="Emergency Alerts":

    st.title("Emergency Alerts")

    df=pd.DataFrame(st.session_state.complaints)

    alerts=df[df["urgency"]=="High"]

    if len(alerts)==0:
        st.success("No emergencies")

    else:

        for _,row in alerts.iterrows():

            st.error(
                f"🚨 {row['summary']} at {row['location']}"
            )