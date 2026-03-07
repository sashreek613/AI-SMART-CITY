import streamlit as st
import pandas as pd
import folium
import requests
import pydeck as pdk
from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster
from datetime import datetime
from geopy.geocoders import Nominatim
from textblob import TextBlob
from streamlit_js_eval import get_geolocation
from streamlit_autorefresh import st_autorefresh

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
# URGENCY AI
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

    else:
        return "General","City Services",urgency

# -------------------------
# SIDEBAR
# -------------------------

st.sidebar.title("Smart City Command Center")

page = st.sidebar.radio(
    "Navigation",
    ["Submit Complaint","Dashboard","City Map","Analytics","Risk Dashboard","3D Heatmap"]
)

# -------------------------
# SUBMIT PAGE
# -------------------------

if page == "Submit Complaint":

    st.title("Submit Complaint")

    complaint = st.text_area("Describe issue")

    location = st.text_input("Enter location")

    lat = None
    lon = None
    address = location

    if location:
        lat,lon,address = get_coordinates(location)

    if st.button("Use Current Location"):

        gps = get_geolocation()

        if gps:
            lat = gps["coords"]["latitude"]
            lon = gps["coords"]["longitude"]
            address = reverse_geocode(lat,lon)

    st.subheader("Select location on map")

    map_select = folium.Map(location=[32.37,-86.30],zoom_start=12)

    map_data = st_folium(map_select,height=400)

    if map_data and map_data["last_clicked"]:

        lat = map_data["last_clicked"]["lat"]
        lon = map_data["last_clicked"]["lng"]

        address = reverse_geocode(lat,lon)

    if st.button("Submit Complaint"):

        category,department,urgency = classify(complaint)

        st.session_state.complaints.append({

            "complaint":complaint,
            "location":address,
            "category":category,
            "department":department,
            "urgency":urgency,
            "lat":lat,
            "lon":lon,
            "time":datetime.now()

        })

        st.success("Complaint submitted")

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

        st.subheader("Live Complaint Feed")

        st.dataframe(df.sort_values("time",ascending=False))

        st.download_button(
            "Download Complaints CSV",
            df.to_csv(index=False),
            "complaints.csv"
        )

# -------------------------
# CITY MAP
# -------------------------

elif page == "City Map":

    st.title("City Issues Map")

    m = folium.Map(location=[32.37,-86.30],zoom_start=12)

    cluster = MarkerCluster().add_to(m)

    heat=[]

    citizen_df = pd.DataFrame(st.session_state.complaints)

    for _,row in citizen_df.iterrows():

        if pd.notnull(row["lat"]) and pd.notnull(row["lon"]):

            folium.Marker(
                [row["lat"],row["lon"]],
                popup=row["complaint"],
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

# -------------------------
# ANALYTICS
# -------------------------

elif page == "Analytics":

    st.title("City Analytics")

    df = pd.DataFrame(st.session_state.complaints)

    if len(df)==0:
        st.info("No analytics yet")

    else:

        st.subheader("Department Workload")
        st.bar_chart(df["department"].value_counts())

        st.subheader("Location Hotspots")
        st.bar_chart(df["location"].value_counts())

# -------------------------
# RISK DASHBOARD
# -------------------------

elif page == "Risk Dashboard":

    st.title("City Risk Score Dashboard")

    df = pd.DataFrame(st.session_state.complaints)

    if len(df)==0:
        st.info("No data")

    else:

        def risk_score(row):

            if row["urgency"]=="High":
                return 5
            elif row["urgency"]=="Medium":
                return 3
            else:
                return 1

        df["risk"] = df.apply(risk_score,axis=1)

        risk = df.groupby("location")["risk"].sum()

        risk_df = risk.sort_values(ascending=False).reset_index()

        risk_df.columns=["Location","Risk Score"]

        st.dataframe(risk_df)

        st.bar_chart(risk_df.set_index("Location"))

# -------------------------
# 3D HEATMAP
# -------------------------

elif page == "3D Heatmap":

    st.title("3D City Issue Heatmap")

    df = pd.DataFrame(st.session_state.complaints)

    if len(df)==0:
        st.info("No complaint data")

    else:

        df = df.dropna(subset=["lat","lon"])

        if len(df)==0:
            st.info("No location data available")

        else:

            df["lat"] = pd.to_numeric(df["lat"])
            df["lon"] = pd.to_numeric(df["lon"])

            layer = pdk.Layer(
                "HexagonLayer",
                data=df,
                get_position="[lon, lat]",
                radius=200,
                elevation_scale=4,
                elevation_range=[0,1000],
                pickable=True,
                extruded=True,
            )

            view_state = pdk.ViewState(
                latitude=df["lat"].mean(),
                longitude=df["lon"].mean(),
                zoom=11,
                pitch=50,
            )

            deck = pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                map_style="mapbox://styles/mapbox/dark-v10"
            )

            st.pydeck_chart(deck)