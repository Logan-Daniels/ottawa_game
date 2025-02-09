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
    layout="wide",
)

# Updated CSS to constrain scrolling and reduce spacing
st.markdown(
    """
    <style>
        /* Fix viewport height and prevent page scrolling */
        section[data-testid="stSidebar"] {
            display: none;
        }
        
        .main .block-container {
            padding-top: 1rem !important;
            padding-left: 1rem;
            padding-right: 1rem;
            padding-bottom: 0 !important;
            max-width: 100%;
            width: 100%;
            overflow-x: hidden;
            height: 100vh;
        }
        
        /* Remove extra spacing around title */
        h1 {
            margin: 30 !important;
            padding: 30 !important;
            /*line-height: 1.2 !important;*/
        }
        
        /* Center align column contents */
        div[data-testid="column"] {
            text-align: center;
            width: auto !important;
            min-width: 0;
            padding: 0 !important;
        }
        
        /* Adjust horizontal block layout */
        div[data-testid="stHorizontalBlock"] {
            width: 100%;
            margin: 0 auto;
            gap: 0.5rem;
            padding: 0 !important;
        }
        
        /* Make buttons more compact */
        div[data-testid="stHorizontalBlock"] button {
            width: 100% !important;
            min-width: 0 !important;
            padding: 0.5rem !important;
            margin: 0 !important;
        }
        
        /* Remove extra padding around elements */
        .element-container {
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* Ensure map container doesn't overflow */
        .stFoliumMap {
            width: 100% !important;
            max-width: 400px !important;
            margin: 0 auto !important;
        }
        
        /* Remove padding around map */
        .stFoliumMap > div {
            margin: 0.5rem auto !important;
        }
        
        @media (max-width: 640px) {
            div[data-testid="stHorizontalBlock"] button {
                font-size: 1.2rem !important;
            }
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
if "zoom" not in st.session_state:
    st.session_state.zoom = 13

# Create map
m = folium.Map(
    min_zoom = 13,
    location = [st.session_state.lat, st.session_state.lon],
    zoom_start = st.session_state.zoom,
)

folium.TileLayer(
        tiles = 'https://api.maptiler.com/maps/voyager/{z}/{x}/{y}.png?key=' + st.secrets["map_tiler"],
        attr = '<a href="https://www.maptiler.com/copyright/" target="_blank">&copy; MapTiler</a>',
        api_key = st.secrets["map_tiler"],
        min_zoom = 13,
        max_zoom = 21,
    ).add_to(m)

team_colours = ("red", "blue", "green")
# Add regions to map
for region in range(len(df_region_points.index.unique())):
    folium.Polygon(
        locations = df_region_points.loc[region],
        color = team_colours[region],
        fill = True,
        fill_opacity = 0.2,
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
st.markdown("<h1 style='text-align: center; color: blue;'>LIT's Ottawa Game</h1>", unsafe_allow_html=True)

# Place map in a container to control its width
map_container = st.container()
with map_container:
    output = st_folium(
        m,
        height = 400,
        width = None,
    )

# Create a container for the buttons with minimal spacing
button_container = st.container()
with button_container:
    col1, col2 = st.columns([1, 1])  # Equal width columns
    with col1:
        if st.button("✛"):
            st.session_state.getting_location = True
            
    with col2:
        if st.button("🏠"):
            st.session_state.getting_location = False
            st.session_state.lat = centre.y
            st.session_state.lon = centre.x
            st.session_state.zoom = 13
            st.rerun()

if "getting_location" in st.session_state and st.session_state.getting_location:
    try:
        loc = get_geolocation()["coords"]
    except TypeError:
        raise PermissionError("Change site settings to allow location")
    if loc:  # Ensure location data is valid
        st.session_state.lat = loc["latitude"]
        st.session_state.lon = loc["longitude"]
        st.session_state.getting_location = False  # Reset flag
        st.session_state.zoom = output["zoom"]
        st.rerun()