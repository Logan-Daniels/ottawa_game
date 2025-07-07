import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
import os
import pymongo
import geopandas as gpd
from shapely.geometry import Point

def rgb_to_hex_fstring(r, g, b):
    """Converts RGB values (0-255) to a hexadecimal color code string."""
    return f'#{r:02X}{g:02X}{b:02X}'

# Function to create popup HTML with team scores
def create_popup_html(zone_number, orange_data, pink_data):
    orange_points = orange_data.get(f"zone_{zone_number}", 0) if orange_data else 0
    pink_points = pink_data.get(f"zone_{zone_number}", 0) if pink_data else 0
    
    html = f"""
    <div style="font-family: Arial, sans-serif; min-width: 150px;">
        <h4 style="margin: 0; text-align: center;">Zone {zone_number}</h4>
        <div style="margin: 10px 0;">
            <div style="color: #FF9600; font-weight: bold;">🟠 Orange: {orange_points}</div>
            <div style="color: #FF0096; font-weight: bold;">🩷 Pink: {pink_points}</div>
        </div>
    </div>
    """
    return html

# Function to get the nearest zone to user location
def get_nearest_zone(user_lat, user_lon, gdf):
    if user_lat is None or user_lon is None:
        return None
    
    user_point = Point(user_lon, user_lat)
    user_gdf = gpd.GeoDataFrame([1], geometry=[user_point], crs = "EPSG:4326")
    
    # Find nearest zone
    nearest = gpd.sjoin_nearest(user_gdf, gdf, how = "left")
    closest_zone_idx = nearest.index_right.iloc[0]
    
    return closest_zone_idx + 1  # Return 1-indexed zone number

st.set_page_config(
    page_title = "LITs' Ottawa Game",
    page_icon = os.path.join(os.getcwd(), "images", "kinneret_logo.png"),
    layout = "wide",
)

centre = {"lat": 45.4248, "lon": -75.69522}
challenges = (
    {
        "location": "Fairmount Château Laurier",
        "lat": 45.42566,
        "lon": -75.69529,
        "title": "Fancy Washroom",
        "challenge": "Have a team member use a toilet in the Fairmount Château Laurier.",
        "points": 300,
        "zone": 8,
        "link": "https://maps.google.com/?cid=8854846295512453637",
    },
    {
        "location": "National Gallery of Canada",
        "lat": 45.42935,
        "lon": -75.69727,
        "title": "Recreate Maman",
        "challenge": "Take a photo of one camper making a bridge or 4 legged pose and another camper overtop of them to be the other 4 spider legs.",
        "points": 100,
        "zone": 8,
        "link": "https://maps.google.com/?cid=7418760184671049655",
    },
    {
        "location": "Kìwekì Point",
        "lat": 45.4296,
        "lon": -75.70098,
        "title": "Explore for an Explorer",
        "challenge": "Find and recreate the Samuel de Champlain statue at Kìwekì Point without looking up the exact location of the statue (it is in the park).",
        "points": 200,
        "zone": 8,
        "link": "https://maps.google.com/?cid=10074131504615629002",
    },
)

# Updated CSS to constrain scrolling and reduce spacing
st.markdown(
    """
    <link rel="manifest" href="data:application/json;charset=utf-8,{manifest_json}">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#ffffff">
    <link rel="apple-touch-icon" href="images/kinneret_logo.png">

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

st.markdown("<h1 style='text-align: center; color: blue;'>LITs' Ottawa Game</h1>", unsafe_allow_html = True)

gdf = gpd.read_file(os.path.join(os.getcwd(), "data", "zones.kml"), driver = "KML")

if "team" not in st.session_state:
    st.session_state.team = None
if "game_id" not in st.session_state:
    st.session_state.game_id = None
if "last_clicked_challenge" not in st.session_state:
    st.session_state.last_clicked_challenge = None

if st.session_state.team == None or st.session_state.game_id == None:
    game_id = st.text_input("Enter your game ID:", key = "game_id_input", placeholder = "Enter your game ID here")
    team = st.radio("Team:", ["Orange", "Pink"], key = "team_radio", horizontal = True)
    
    if st.button("Go!") and team and game_id:
        st.session_state.team = team.lower()
        st.session_state.game_id = game_id
        
        try:
            # Add timeout and retry parameters
            client = pymongo.MongoClient(
                st.secrets["mongo_url"],
                serverSelectionTimeoutMS = 15000,  # 15 second timeout
                connectTimeoutMS = 15000,
                socketTimeoutMS = 15000
            )
            
            # Test the connection
            client.admin.command('ping')
            
            db = client["ottawa-game"]
            collection = db[game_id]
            
            # Check if this is a new game and initialize team data
            if game_id not in db.list_collection_names():
                teams = ["orange", "pink"]
                team_documents = []
                
                for team_name in teams:
                    team_data = {"_id": team_name, "balance": 0}
                    # Add zones 1-9
                    for zone_num in range(1, 10):
                        team_data[f"zone_{zone_num}"] = 0
                    # Add completed challenges list
                    team_data["completed_challenges"] = []
                    team_documents.append(team_data)
                
                # Insert all team documents
                collection.insert_many(team_documents)
            
            st.session_state.zoom = 14

            st.rerun()
            
        except Exception as e:
            st.error(f"Database connection failed: {e}")
            st.info("Please check your internet connection and try again.")

else:
    client = pymongo.MongoClient(st.secrets["mongo_url"])
    db = client["ottawa-game"]
    collection = db[st.session_state.game_id]

    # Fetch team data
    try:
        orange_data = collection.find_one({"_id": "orange"})
        pink_data = collection.find_one({"_id": "pink"})
    except Exception as e:
        st.error(f"Error fetching team data: {e}")
        orange_data = None
        pink_data = None

    if "lat" not in st.session_state:
        st.session_state.lat = None
    if "lon" not in st.session_state:
        st.session_state.lon = None
    if "zoom" not in st.session_state:
        st.session_state.zoom = 14

    m = folium.Map(
        min_zoom = 5,
        location = [centre["lat"], centre["lon"]],  # Ottawa's approximate center
        zoom_start = 14,
    )

    if st.session_state.lat != None and st.session_state.lon != None:
        folium.Marker(
            location = [st.session_state.lat, st.session_state.lon] if st.session_state.lat and st.session_state.lon else [centre["lat"], centre["lon"]],
            icon = folium.DivIcon(
                html = f'<i class="fa fa-location-crosshairs" style="color: #0050ff; font-size: 20px;"></i>',
                icon_size = (25, 25),
                icon_anchor = (12.5, 12.5)
            )
        ).add_to(m)
    else:
        st.session_state.getting_location = True

    # Function to determine zone color based on team points
    def get_zone_color(zone_number, orange_data, pink_data):
        if orange_data and pink_data:
            orange_points = orange_data.get(f"zone_{zone_number}", 0)
            pink_points = pink_data.get(f"zone_{zone_number}", 0)
            
            if orange_points > pink_points:
                return rgb_to_hex_fstring(255, 150, 0)  # Orange team winning
            elif pink_points > orange_points:
                return rgb_to_hex_fstring(255, 0, 150)  # Pink team winning
            else:
                return rgb_to_hex_fstring(255, 75, 75)  # Tie
        else:
            return rgb_to_hex_fstring(255, 75, 75)  # Default color if no data

    # Get the nearest zone for highlighting
    nearest_zone = get_nearest_zone(st.session_state.lat, st.session_state.lon, gdf)
    
    for zone in range(len(gdf)):
        x_coords, y_coords = gdf.geometry.iloc[zone].exterior.coords.xy
        coords = [(y, x) for x, y in zip(x_coords, y_coords)]
        
        # Get color based on team points (zone numbers are 1-indexed)
        zone_number = zone + 1
        zone_color = get_zone_color(zone_number, orange_data, pink_data)
        
        # Create popup content
        popup_html = create_popup_html(zone_number, orange_data, pink_data)
        
        # Highlight the nearest zone with higher opacity and border weight
        is_nearest = (nearest_zone == zone_number)
        fill_opacity = 0.6 if is_nearest else 0.3
        border_weight = 5 if is_nearest else 3
        
        folium.Polygon(
            locations = coords,
            color = zone_color,
            fill = True,
            fill_opacity = fill_opacity,
            weight = border_weight,
            popup = folium.Popup(popup_html, max_width = 200)
        ).add_to(m)

    # Get completed challenges for current team
    current_team_data = orange_data if st.session_state.team == "orange" else pink_data
    completed_challenges = current_team_data.get("completed_challenges", []) if current_team_data else []
    
    # Only show challenges that haven't been completed by this team
    for i, challenge in enumerate(challenges):
        if challenge["title"] not in completed_challenges:
            folium.Marker(
                location = [challenge["lat"], challenge["lon"]],
                icon = folium.DivIcon(
                    html = f'<i class="fa-solid fa-trophy" style="color: #{"FFD700" if challenge["points"] >= 300 else "C0C0C0" if challenge["points"] >= 200 else "CD7F32"}; font-size: 25px;"></i>',
                    icon_size = (24, 16),
                    icon_anchor = (12, 8)
                ),
                popup = folium.Popup(
                    f"""<b style="text-align: center;"><h3>{challenge['location']}</h3>{challenge['title']}</b><br><i>Points: {challenge['points']}</i><br>{challenge['challenge']}<br><a href='{challenge['link']}' target='_blank'>View on Google Maps</a>""",
                    max_width = 300,
                ),
                tooltip = challenge['title'],
            ).add_to(m)
        
    folium.TileLayer(
            tiles = 'https://api.maptiler.com/maps/voyager/{z}/{x}/{y}.png?key=' + st.secrets["map_tiler"],
            attr = '<a href="https://www.maptiler.com/copyright/" target="_blank">&copy; MapTiler</a>',
            api_key = st.secrets["map_tiler"],
            min_zoom = 13,
            max_zoom = 21,
        ).add_to(m)

    map_container = st.container()
    with map_container:
        output = st_folium(
            m,
            height = 400,
            width = None,
        )

    # Check if a challenge marker was clicked
    if output["last_object_clicked_popup"] is not None:
        popup_content = output["last_object_clicked_popup"]
        # Find which challenge was clicked based on popup content
        for challenge in challenges:
            if challenge["title"] in popup_content and challenge["title"] not in completed_challenges:
                st.session_state.last_clicked_challenge = challenge
                break

    # Display team info and deposit interface
    if orange_data and pink_data:
        team_color = "#FF9600" if st.session_state.team == "orange" else "#FF0096"
        team_emoji = "🟠" if st.session_state.team == "orange" else "🩷"
        
        st.markdown(f"<h4 style='color: {team_color}; text-align: center;'>{team_emoji} {st.session_state.team.title()} Team {team_emoji}</h4>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='color: {team_color}; text-align: center;'>Balance: {current_team_data.get('balance', 0)} points</h4>", unsafe_allow_html=True)
        
        if nearest_zone is not None:
            col1, col2 = st.columns(2)
            with col1:
                max_deposit = current_team_data.get('balance', 0)
                deposit_amount = st.number_input("Points to deposit:", min_value=0, max_value=max_deposit, value=0)
            with col2:
                if st.button(f"Deposit to Zone {nearest_zone}"):
                    if deposit_amount > 0:
                        # Show deposit confirmation dialog
                        @st.dialog("Confirm Point Deposit")
                        def confirm_deposit():
                            st.write(f"**Zone:** {nearest_zone}")
                            st.write(f"**Points to deposit:** {deposit_amount}")
                            st.write(f"**Your current balance:** {current_team_data.get('balance', 0)} points")
                            st.write(f"**Balance after deposit:** {current_team_data.get('balance', 0) - deposit_amount} points")
                            st.write("---")
                            st.write("Are you sure you want to deposit these points?")
                            
                            col_cancel, col_confirm = st.columns(2)
                            with col_cancel:
                                if st.button("Cancel", type="secondary"):
                                    st.rerun()
                            with col_confirm:
                                if st.button("Confirm Deposit", type="primary"):
                                    try:
                                        # Update database
                                        collection.update_one(
                                            {"_id": st.session_state.team},
                                            {
                                                "$inc": {
                                                    "balance": -deposit_amount,
                                                    f"zone_{nearest_zone}": deposit_amount
                                                }
                                            }
                                        )
                                        st.success(f"Successfully deposited {deposit_amount} points to Zone {nearest_zone}!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error depositing points: {e}")
                        
                        confirm_deposit()
                    else:
                        st.warning("Please enter a deposit amount greater than 0.")
        else:
            st.warning("Please enable location services to deposit points.")

    # Create a container for the buttons with minimal spacing
    button_container = st.container()
    with button_container:
        col1, col2, col3 = st.columns([1, 1, 1])  # Three equal columns
        with col1:
            if st.button("✛"):
                st.session_state.getting_location = True
                
        with col2:
            if st.button("🏠"):
                st.session_state.getting_location = False
                st.session_state.lat = centre["lat"]
                st.session_state.lon = centre["lon"]
                st.session_state.zoom = 14
                st.rerun()
        
        with col3:
            # Challenge completion button
            if st.session_state.last_clicked_challenge is not None:
                challenge = st.session_state.last_clicked_challenge
                if st.button(f"Complete: {challenge['title']} ({challenge['points']} pts)"):
                    # Show challenge completion confirmation dialog
                    @st.dialog("Confirm Challenge Completion")
                    def confirm_challenge():
                        st.write(f"**Challenge:** {challenge['title']}")
                        st.write(f"**Points:** {challenge['points']}")
                        st.write(f"**Location:** {challenge['location']}")
                        st.write(f"**Your current balance:** {current_team_data.get('balance', 0)} points")
                        st.write(f"**Balance after completion:** {current_team_data.get('balance', 0) + challenge['points']} points")
                        st.write("---")
                        st.write("**Challenge Description:**")
                        st.write(challenge['challenge'])
                        st.write("---")
                        st.write("Are you sure you have completed this challenge?")
                        
                        col_cancel, col_confirm = st.columns(2)
                        with col_cancel:
                            if st.button("Cancel", type="secondary"):
                                st.rerun()
                        with col_confirm:
                            if st.button("Confirm Completion", type="primary"):
                                try:
                                    # Update database - add points to balance and mark challenge as completed
                                    collection.update_one(
                                        {"_id": st.session_state.team},
                                        {
                                            "$inc": {"balance": challenge['points']},
                                            "$addToSet": {"completed_challenges": challenge['title']}
                                        }
                                    )
                                    st.success(f"Challenge '{challenge['title']}' completed! +{challenge['points']} points!")
                                    st.session_state.last_clicked_challenge = None
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error completing challenge: {e}")
                    
                    confirm_challenge()
            else:
                st.button("Click a challenge", disabled=True)

    if "getting_location" in st.session_state:
        try:
            loc = get_geolocation()["coords"]
        except TypeError:
            raise PermissionError("Change site settings to allow location")
        if loc:  # Ensure location data is valid
            st.session_state.lat = loc["latitude"]
            st.session_state.lon = loc["longitude"]
            st.session_state.zoom = output["zoom"]
            st.session_state.getting_location = False  # Reset flag