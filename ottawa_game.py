import streamlit as st
import geopandas as gpd
from shapely.geometry import Point, LineString
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
import os
import pandas as pd
from functions import *

st.set_page_config(
    page_title = "LITs' Ottawa Game",
    page_icon = os.path.join(os.getcwd(), "images", "kinneret_logo.png"),
    layout = "wide",
)

st.markdown(
    """
    <style>
        div[data-testid="column"] {
            text-align: center;
        }
    </style>
    """,
    unsafe_allow_html = True,
)

# Read points and set initial CRS
gdf = gpd.read_file(os.path.join(os.getcwd(), "data", "win_locations.csv"))[["name", "geometry"]].set_crs(4326)
df_region_points = pd.read_csv(os.path.join(os.getcwd(), "data", "region_points.csv"))
df_region_points = df_region_points.set_index("region")

# Project to a suitable UTM zone for accurate measurements
utm_crs = gdf.estimate_utm_crs()
gdf_projected = gdf.to_crs(utm_crs)

# Get centre point and other points
centre = gdf.geometry.iloc[3]
points = gdf_projected.iloc[:3]

if "lat" not in st.session_state:
    st.session_state.lat = centre.y
if "lon" not in st.session_state:
    st.session_state.lon = centre.x

# Create map
m = folium.Map(
    min_zoom = 13,
    location = [st.session_state.lat, st.session_state.lon]
)

team_colours = ("red", "blue", "green")
# Add regions to map
for region in range(len(df_region_points.index.unique())):
    folium.Polygon(
        locations = df_region_points.loc[region],
        color = team_colours[region],
        fill = True,
        fill_opacity = 0.3,
        weight = 1
    ).add_to(m)

# Add markers for original and centre points
points = points.to_crs(4326)
for i in range(len(points)):
    folium.Marker(
        location = (points.geometry.iloc[i].y, points.geometry.iloc[i].x),
        icon = folium.Icon(
            color = team_colours[i],
            icon_color = "gold",
            icon = "trophy",
            prefix = "fa"
        ),
        popup = f'<p style="text-align: center;"><b>{points.iloc[i]["name"]}</b></p>'
    ).add_to(m)


# Site Design:
st.markdown("<h1 style='text-align: center; color: blue;'>LIT's Ottawa Game</h1>", unsafe_allow_html = True)

st_folium(
    m,
    height = 400,
    width = 400,
)

col1, col2 = st.columns(2)
with col2:
    if st.button(":house:"):
        st.session_state.getting_location = False
        st.session_state.lat = centre.y
        st.session_state.lon = centre.x
        st.rerun()

with col1:
    if st.button("✛"):
        st.session_state.getting_location = True

if "getting_location" in st.session_state and st.session_state.getting_location:
    try:
        loc = get_geolocation()["coords"]
    except TypeError:
        raise PermissionError("Change site settings to allow location")
    if loc:  # Ensure location data is valid
        st.session_state.lat = loc["latitude"]
        st.session_state.lon = loc["longitude"]
        st.session_state.getting_location = False # Reset flag
        st.rerun()