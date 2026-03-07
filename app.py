import streamlit as st
import pandas as pd
import folium
import requests
from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster
from datetime import datetime
from geopy.geocoders import Nominatim
from textblob import TextBlob
from streamlit_autorefresh import st_autorefresh
from PIL import Image

st.set_page_config(page_title="Smart City AI Command Center", layout="wide")

# -------------------------
# AUTO REFRESH
# -------------------------

st_autorefresh(interval=10000, key="refresh")

# -------------------------
# GEOLOCATOR
# -------------------------

geolocator = Nominatim(user_agent="smart_city_ai")

# -------------------------
# SESSION STORAGE
# -------------------------

if "complaints" not in st.session_state:
    st.session_state.complaints = []

# -------------------------
# LOAD CITY DATA
# -------------------------

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

# -------------------------
# GEO FUNCTIONS
# -------------------------

def get_coordinates(location):

    try:
        loc = geolocator.geocode(location)

        if loc:
            return loc.latitude, loc.longitude, loc.address

    except:
        pass

    return None, None, location


def reverse_geocode(lat, lon):

    try:
        loc = geolocator.reverse((lat, lon))

        if loc:
            return loc.address

    except:
        pass

    return f"{lat},{lon}"

# -------------------------
# AI SUMMARIZER
# -------------------------

def summarize(text):

    blob = TextBlob(text)
    sentences = blob.sentences

    if len(sentences) > 1:
        return str(sentences[0])

    return text[:80]

# -------------------------
# URGENCY DETECTION
# -------------------------

def detect_urgency(text):

    text = text.lower()
    score = 0

    high_keywords = ["broken","fire","accident","sewage","leak"]
    medium_keywords = ["traffic","signal","garbage","pothole"]

    for word in high_keywords:
        if word in text:
            score += 3

    for word in medium_keywords:
        if word in text:
            score += 2

    sentiment = TextBlob(text).sentiment.polarity

    if sentiment < -0.3:
        score += 1

    if score >= 5:
        return "High"
    elif score >= 3:
        return "Medium"
    else:
        return "Low"

# -------------------------
# CLASSIFIER
# -------------------------

def classify(text):

    text = text.lower()
    urgency = detect_urgency(text)

    if "garbage" in text:
        return "Sanitation","Waste Management",urgency

    elif "light" in text:
        return "Infrastructure","Electrical Department",urgency

    elif "water" in text:
        return "Water Supply","Water Department",urgency

    elif "traffic" in text:
        return "Traffic","Traffic Department",urgency

    elif "pothole" in text:
        return "Road Damage","Road Department",urgency

    else:
        return "General","City Services",urgency

# -------------------------
# SIDEBAR
# -------------------------

st.sidebar.title("Smart City Command Center")

page = st.sidebar.radio(
    "Navigation",
    [
        "Submit Complaint",
        "Dashboard",
        "City Map",
        "Analytics",
        "Risk Dashboard",
        "Emergency Alerts"
    ]
)

# -------------------------
# SUBMIT COMPLAINT
# -------------------------

if page == "Submit Complaint":

    st.title("Submit Complaint")

    # -------- CURRENT LOCATION BUTTON --------

    if st.button("📍 Use Current Location"):

        gps = get_geolocation()

        if gps:
            st.session_state.current_lat = gps["coords"]["latitude"]
            st.session_state.current_lon = gps["coords"]["longitude"]

            address = reverse_geocode(
                st.session_state.current_lat,
                st.session_state.current_lon
            )

            st.session_state.current_address = address

            st.success(f"Location detected: {address}")

    # -------- COMPLAINT FORM --------

    with st.form("complaint_form", clear_on_submit=True):

        complaint = st.text_area("Describe issue")

        location = st.text_input("Enter location")

        image = st.file_uploader("Upload Photo of Issue", type=["jpg","png","jpeg"])

        if image:
            st.image(image,width=300)

        lat = None
        lon = None
        address = location

        # If manual location entered
        if location:
            lat,lon,address = get_coordinates(location)

        # If GPS location used
        if "current_lat" in st.session_state:

            lat = st.session_state.current_lat
            lon = st.session_state.current_lon
            address = st.session_state.current_address

        st.subheader("Select location on map")

        map_select = folium.Map(location=[32.37,-86.30],zoom_start=12)

        map_data = st_folium(map_select,height=400)

        if map_data and map_data["last_clicked"]:

            lat = map_data["last_clicked"]["lat"]
            lon = map_data["last_clicked"]["lng"]

            address = reverse_geocode(lat,lon)

        submitted = st.form_submit_button("Submit Complaint")

        if submitted:

            category,department,urgency = classify(complaint)

            summary = summarize(complaint)

            st.session_state.complaints.append({

                "complaint":complaint,
                "summary":summary,
                "location":address,
                "category":category,
                "department":department,
                "urgency":urgency,
                "lat":lat,
                "lon":lon,
                "image":image,
                "time":datetime.now()

            })

            st.success("Complaint submitted successfully!")
# -------------------------
# DASHBOARD
# -------------------------

elif page == "Dashboard":

    st.title("City Command Center Dashboard")

    df = pd.DataFrame(st.session_state.complaints)

    if len(df) == 0:
        st.info("No complaints submitted yet")

    else:

        c1,c2,c3,c4 = st.columns(4)

        c1.metric("Total Complaints",len(df))
        c2.metric("High Urgency",len(df[df["urgency"]=="High"]))
        c3.metric("Medium Urgency",len(df[df["urgency"]=="Medium"]))
        c4.metric("Low Urgency",len(df[df["urgency"]=="Low"]))

        st.dataframe(df[["summary","location","department","urgency","time"]].sort_values("time",ascending=False))

# -------------------------
# CITY MAP
# -------------------------

elif page == "City Map":

    st.title("City Issues Map")

    m = folium.Map(location=[32.37,-86.30],zoom_start=12)

    cluster = MarkerCluster().add_to(m)

    heat=[]

    df = pd.DataFrame(st.session_state.complaints)

    for _,row in df.iterrows():

        if pd.notnull(row["lat"]) and pd.notnull(row["lon"]):

            folium.Marker(
                [row["lat"],row["lon"]],
                popup=row["summary"],
                icon=folium.Icon(color="red")
            ).add_to(cluster)

            heat.append([row["lat"],row["lon"]])

    if heat:
        HeatMap(heat).add_to(m)

    st_folium(m,width=900,height=600)

# -------------------------
# ANALYTICS
# -------------------------

elif page == "Analytics":

    st.title("City Analytics")

    df = pd.DataFrame(st.session_state.complaints)

    if len(df)==0:
        st.info("No analytics yet")

    else:

        st.bar_chart(df["department"].value_counts())
        st.bar_chart(df["location"].value_counts())

# -------------------------
# RISK DASHBOARD
# -------------------------

elif page == "Risk Dashboard":

    st.title("City Risk Prediction Dashboard")

    df = pd.DataFrame(st.session_state.complaints)

    if len(df)==0:
        st.info("No risk data yet")

    else:

        def risk_score(row):

            if row["urgency"]=="High":
                return 5
            elif row["urgency"]=="Medium":
                return 3
            else:
                return 1

        df["risk"] = df.apply(risk_score,axis=1)

        total_risk = df["risk"].sum()

        if total_risk < 10:
            level = "Low"
        elif total_risk < 25:
            level = "Moderate"
        elif total_risk < 50:
            level = "High"
        else:
            level = "Critical"

        st.metric("City Risk Level", level)
        st.metric("Total Risk Score", total_risk)

        risk_df = df.groupby("location")["risk"].sum().sort_values(ascending=False).reset_index()
        risk_df.columns=["Location","Risk Score"]

        st.dataframe(risk_df)
        st.bar_chart(risk_df.set_index("Location"))

# -------------------------
# EMERGENCY ALERTS
# -------------------------

elif page == "Emergency Alerts":

    st.title("🚨 Live Emergency Alerts")

    df = pd.DataFrame(st.session_state.complaints)

    if len(df)==0:
        st.info("No alerts")

    else:

        alerts = df[df["urgency"]=="High"]

        if len(alerts)==0:
            st.success("No emergency alerts")

        else:

            st.error("⚠ HIGH PRIORITY INCIDENTS DETECTED")

            for _,row in alerts.iterrows():

                st.warning(
                    f"""
                    🚨 **Emergency Issue**

                    **Location:** {row['location']}  
                    **Department:** {row['department']}  
                    **Issue:** {row['summary']}  
                    **Reported:** {row['time']}
                    """
                )