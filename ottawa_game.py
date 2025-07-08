import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
import os
import pymongo
import geopandas as gpd
from shapely.geometry import Point
import random

def rgb_to_hex_fstring(r, g, b):
    """Converts RGB values (0-255) to a hexadecimal color code string."""
    return f'#{r:02X}{g:02X}{b:02X}'

def test_mongo_connection():
    """Test MongoDB connection with better error handling"""
    try:
        # Try with shorter timeout first
        client = pymongo.MongoClient(
            st.secrets["mongo_url"],
            serverSelectionTimeoutMS=8000,  # 8 seconds
            connectTimeoutMS=8000,
            socketTimeoutMS=8000,
            retryWrites=True,
            w='majority'
        )
        
        # Test the connection
        client.admin.command('ping')
        return client, None
        
    except pymongo.errors.ServerSelectionTimeoutError as e:
        return None, f"Server selection timeout - please check your internet connection and MongoDB Atlas settings: {str(e)}"
    except pymongo.errors.ConnectionFailure as e:
        return None, f"Connection failure - check if your IP is whitelisted in MongoDB Atlas: {str(e)}"
    except pymongo.errors.ConfigurationError as e:
        return None, f"Configuration error - check your connection string: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

# Function to create popup HTML with team scores
def create_popup_html(zone_number, orange_data, pink_data):
    orange_points = orange_data.get(f"zone_{zone_number}", 0) if orange_data else 0
    pink_points = pink_data.get(f"zone_{zone_number}", 0) if pink_data else 0
    
    html = f"""
    <div style="font-family: Arial, sans-serif; min-width: 150px;">
        <h4 style="margin: 0; text-align: center;">Zone {zone_number}</h4>
        <div style="margin: 10px 0;">
            <div style="color: #FF9600; font-weight: bold;">🧡 Orange: {orange_points}</div>
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
    user_gdf = gpd.GeoDataFrame([1], geometry=[user_point], crs="EPSG:4326")
    
    # Find nearest zone
    nearest = gpd.sjoin_nearest(user_gdf, gdf, how="left")
    closest_zone_idx = nearest.index_right.iloc[0]
    
    return closest_zone_idx + 1  # Return 1-indexed zone number

# Define all cards
CARDS = {
    "lemon_phylactery": {
        "title": "Curse of the Lemon Phylactery",
        "description": "Before your opponent can deposit points or complete another challenge, they must first affix a lawfully obtained lemon or lime fruit to one of their campers for the rest of the game. If the citrus detaches from the camper before the end of the program, the team must memorize and correctly recite all members of the Canadian cabinet before they can continue with anything else. The office will reimburse you up to $10 for a lemon and/or materials to attach it to a camper. Make sure to keep any receipts.",
        "type": "curse",
        "link": "https://www.pm.gc.ca/en/cabinet"
    },
    "gamblers_feet": {
        "title": "Curse of the Gambler's Feet",
        "description": "The cursed team must set a timer for 10 minutes. During those 10 minutes, they must roll a die to move in any direction. They may only take as many steps as they roll until they have to roll again.",
        "type": "curse",
        "link": "https://g.co/kgs/WJ82Wo9",
        "auto_clear": True
    },
    "struck_gold": {
        "title": "Advantage: You struck gold!",
        "description": "Your next challenge is worth 1.5 times its value! You can't draw another card until you complete a challenge, though.",
        "type": "advantage"
    },
    "luxury_car": {
        "title": "Curse of the Luxury Car",
        "description": "Take a photo of a car. The cursed team must take a photo of a more expensive car before your opponent can deposit points or complete another challenge. You must text a photo of your car and input its minimum retail price.",
        "type": "curse_with_input",
        "link": "https://carcostcanada.com/Home/Detailed"
    },
    "risky_geography": {
        "title": "Risky Trivia: Geography",
        "description": "You will be asked a trivia question. You can wager your points below. If you get it right, you will get three times as much back. If you get it wrong, you will lose the points you wagered. You cannot look up the answer.",
        "type": "risky_trivia",
        "question": "What is the population of metropolitan Ottawa? (Answer within 200,000 and it will be considered correct).",
        "answer": 1488307,
        "tolerance": 200000
    },
    "risky_politics": {
        "title": "Risky Trivia: Politics",
        "description": "You will be asked a multiple-choice trivia question. You can wager your points below. If you get it right, you will get three times as much back. If you get it wrong, you will lose the points you wagered. You cannot look up the answer.",
        "type": "risky_trivia_mc",
        "question": "Which of these people was not a prime minister of Canada?",
        "options": ["Robert Borden", "Kim Campbell", "Rick Mercer", "Louis St. Laurent"],
        "answer": "Rick Mercer"
    },
    "risky_history": {
        "title": "Risky Trivia: History",
        "description": "You will be asked a multiple-choice trivia question. You can wager your points below. If you get it right, you will get three times as much back. If you get it wrong, you will lose the points you wagered. You cannot look up the answer.",
        "type": "risky_trivia_mc",
        "question": "Which of these cities was not a capital of the United Province of Canada before Ottawa was made the permanent capital in 1857?",
        "options": ["London, Ontario", "Toronto, Ontario", "Montreal, Quebec", "Quebec City, Quebec", "Kingston, Ontario"],
        "answer": "London, Ontario"
    },
    "cairn": {
        "title": "Curse of the Cairn",
        "description": "You have one attempt to stack as many rocks on top of each other as you can in a freestanding tower. Each rock may only touch one other rock. Once you have added a rock to the tower, it may not be removed. Before adding another rock, the tower must stand for at least five seconds. If at any point, any rock other than the base rock touches the ground, your tower has fallen. The cursed team must then construct a rock tower of the same number of rocks under the same parameters.",
        "type": "curse_with_input"
    },
    "bird_guide": {
        "title": "Curse of the Bird Guide",
        "description": "You have one chance to film a bird for as long as possible, up to 7 minutes straight. If, at any point, the bird leaves the frame, your timer is stopped. The cursed team must film a bird for a longer time than you before they can deposit points or complete another challenge.",
        "type": "curse_with_input"
    },
    "right_turn": {
        "title": "Curse of the Right Turn",
        "description": "The cursed team will have to set a 12 minute timer. Until the end of that timer, they can only go straight or right at any street intersection.",
        "type": "curse",
        "auto_clear": True
    }
}

st.set_page_config(
    page_title="LITs' Ottawa Game",
    page_icon=os.path.join(os.getcwd(), "images", "kinneret_logo.png"),
    layout="wide",
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
   "challenge": "Take a photo of one camper making a bridge or 4-legged pose and another camper overtop of them to be the other 4 spider legs.",
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
{
   "location": "Bytown Museum",
   "lat": 45.42586,
   "lon": -75.69767,
   "title": "",
   "challenge": """Watch <a target="_blank" href="https://www.youtube.com/watch?v=SVsQuv8P9-g">this short video</a> about the Bytown Museum and the history of Ottawa outside the Bytown Museum.""",
   "points": 100,
   "zone": 1,
   "link": "https://maps.google.com/?cid=5318761341977640144",
},
{
   "location": "Senate of Canada",
   "lat": 45.42477,
   "lon": -75.69399,
   "title": "Identify the Famous Five",
   "challenge": """Find the statues of the Famous Five suffragettes outside the Supreme Court at a monument called "Women Are Persons!" Read out <a target="_blank" href="https://www.canada.ca/en/canadian-heritage/services/art-monuments/monuments/women-are-persons.html">this very short article</a>. Spend at least 30 seconds discussing the women's suffrage movement in Canada. Then, all of the campers must learn and recite all of their names and read any plaques that may accompany the statues to complete the challenge.""",
   "points": 100,
   "zone": 6,
   "link": "https://maps.google.com/?cid=761047823053711970",
},
{
   "location": "National Arts Centre",
   "lat": 45.42327,
   "lon": -75.69338,
   "title": "Enjoy some Canadian art",
   "challenge": "Listen to (and appreciate) all of Welcome to the Rock from the viral Canadian musical Come From Away.",
   "points": 100,
   "zone": 3,
   "link": "https://maps.google.com/?cid=2011512308839086810",
},
{
   "location": "Ottawa Jail Hostel",
   "lat": 45.424749,
   "lon": -75.688747,
   "title": "The Jail Hostel",
   "challenge": """Enter the Arts Court at <a target="_blank" href="https://maps.app.goo.gl/Y3kkZHfwK7uUQjRv7">2 Daly Ave</a> (the former courthouse and find the 2 publicly accessible jail cells in the Arts Court. Once there, read <a target="_blank" href="https://www.atlasobscura.com/places/ottawa-jail-hostel">this article</a> about the connected Ottawa Jail Hostel. If you spend at least 8 minutes looking for the cells unsuccessfully, you can read the article outside the entrance to the hostel at <a target="_blank" href="https://maps.app.goo.gl/Y3kkZHfwK7uUQjRv7">75 Nicholas St</a>.""",
   "points": 300,
   "zone": 6,
   "link": "https://maps.app.goo.gl/Y3kkZHfwK7uUQjRv7",
},
{
   "location": "Centennial Flame",
   "lat": 45.42373,
   "lon": -75.6987,
   "title": "Stand on Guard for Thee",
   "challenge": "Find a Mountie in their formal uniform guarding the parliament. Take a photo of all the campers in your group mimicking their pose alongside them.",
   "points": 200,
   "zone": 2,
   "link": "https://maps.google.com/?cid=9981869545010240994",
},
{
   "location": "Rideau Centre",
   "lat": 45.42589,
   "lon": -75.69208,
   "title": "Find a Prime Minister",
   "challenge": "Before 9pm: Take a photo of a book (supposedly) written by a Prime Minister the !ndigo store at the Rideau Centre without asking an employee. After the Rideau Centre closes at 9pm, you can instead photograph the name of a Prime Minister in the Rideau LRT station connected to the mall without the help of any employees there. You cannot write the name yourself or find it on a mobile device.",
   "points": 300,
   "zone": 6,
   "link": "https://maps.app.goo.gl/8qrvtrwQyEGQE3bz9",
},
{
   "location": "House of Commons",
   "lat": 45.42332,
   "lon": -75.7005,
   "title": "Drag the Speaker of the House",
   "challenge": """There is a tradition that a newly elected Speaker of the House is dragged to their chair, because, historically, British speakers risked execution if the news they reported to the king was displeasing. Watch <a target="_blank" href="https://www.youtube.com/shorts/HIQ1VyJA1vM">this video of House Speaker Francis Scarpaleggia being dragged to his seat</a>. Then pick up a camper (with the campers) and carry them for at least 20 metres (66').""",
   "points": 200,
   "zone": 2,
   "link": "https://maps.google.com/?cid=13333871194299290015",
},
{
   "location": "City Hall",
   "lat": 45.4208,
   "lon": -75.68999,
   "title": "O Canada",
   "challenge": "Sing the national anthem (bilingually)",
   "points": 100,
   "zone": 3,
   "link": "https://maps.google.com/?cid=9794861075158029403",
},
{
   "location": "Supreme Court of Canada",
   "lat": 45.42185,
   "lon": -75.70537,
   "title": "The Scales of Justice",
   "challenge": "Use materials found in nature to make a scale. It must make a T shape with an item hanging from each side of the T that do not touch the ground.",
   "points": 300,
   "zone": 1,
   "link": "https://maps.app.goo.gl/RSJRh2Lgke2YwgV9A",
},
{
   "location": "Tabaret Hall",
   "lat": 45.42453,
   "lon": -75.68632,
   "title": "Social Anxiety Test",
   "challenge": "Get someone to salute alongside all of the campers in your group in a photo.",
   "points": 200,
   "zone": 6,
   "link": "https://www.google.com/maps?cid=15941439919447695894",
},
{
   "location": "Rideau Canal Locks",
   "lat": 45.4248,
   "lon": -75.69522,
   "title": "Melted Ice Skating",
   "challenge": "The Rideau Canal Skateway is the longest skating venue in the world … in winter. Have two campers try to skate on land. They must move at least 10 metres (33') each without either of their feet ever losing contact with the ground completely.",
   "points": 200,
   "zone": 3,
   "link": "https://www.google.com/maps/place/Rideau+Canal,+Locks+1+-+8+-+Ottawa/@45.4248006,-75.695228,17z/data=!3m1!4b1!4m6!3m5!1s0x4cce04fe324ecc63:0xf564613f62f3104c!8m2!3d45.4248006!4d-75.695228!16s%2Fg%2F11x9mcwtk?entry=ttu&g_ep=EgoyMDI1MDcwNi4wIKXMDSoASAFQAw%3D%3D",
},
{
   "location": "Confederation Park",
   "lat": 45.42239,
   "lon": -75.69245,
   "title": "Leaving the Comfort Zone",
   "challenge": "Convince a stranger to dab with a camper in a photo in Confederation Park.",
   "points": 200,
   "zone": 4,
   "link": "https://maps.google.com/?cid=5677298280561665746",
},
{
   "location": "ByWard Market",
   "lat": 45.42775,
   "lon": -75.69243,
   "title": "International City",
   "challenge": "Find food items on a menu or at a food stall that is most associated with a specific country/region on 3 different continents besides North America.",
   "points": 200,
   "zone": 7,
   "link": "https://maps.google.com/?cid=2099143516218795562",
},
{
   "location": "Embassy of Mexico",
   "lat": 45.42127,
   "lon": -75.69808,
   "title": "Diplomatic Stroll",
   "challenge": "Without using a phone to navigate, start at the Mexican embassy and photograph another embassy.",
   "points": 300,
   "zone": 9,
   "link": "https://maps.google.com/?cid=14539730619693688087",
},
{
   "location": "uOttawa Station",
   "lat": 45.42076,
   "lon": -75.68275,
   "title": "Find a Train",
   "challenge": "Photograph an LRT vehicle from uOttawa station.",
   "points": 200,
   "zone": 5,
   "link": "https://maps.google.com/?cid=17247419341606602483",
},
{
   "location": "University Square",
   "lat": 45.42181,
   "lon": -75.68296,
   "title": "Ottawa's Got Talent",
   "challenge": "Camper must awkwardly dance for a full minute with no music in University Square on video.",
   "points": 100,
   "zone": 5,
   "link": "https://maps.google.com/?cid=3627643191025529899",
},
{
   "location": "Morisset Library",
   "lat": 45.42326,
   "lon": -75.68402,
   "title": "Find some University Pride",
   "challenge": "Take a photo of a camper with someone wearing University of Ottawa GGs merch. It must say GGs (regular uOttawa merch does not count).",
   "points": 300,
   "zone": 5,
   "link": "https://maps.google.com/?cid=16222945467375777481",
},
{
   "location": "Parliament Hill",
   "lat": 45.42586,
   "lon": -75.70023,
   "title": "Canada's First Rulers",
   "challenge": "Find the statues of Canada's first prime minister and first monarch post-confederation (John A. Macdonald and Queen Victoria). Take a photo of a camper recreating their poses next to each statue.",
   "points": 200,
   "zone": 1,
   "link": "https://maps.google.com/?cid=16265817237874429587",
},
{
   "location": "Saint Patrick Basilica",
   "lat": 45.41649,
   "lon": -75.7009,
   "title": "Find Christ",
   "challenge": "Photograph 5 different crosses on Saint Patrick Basilica.",
   "points": 200,
   "zone": 9,
   "link": "https://maps.google.com/?cid=4958757389272605047",
},
{
   "location": "Ottawa Sign",
   "lat": 45.4275,
   "lon": -75.69449,
   "title": "Recreate the Ottawa Sign",
   "challenge": "Have your campers spell out Ottawa with their bodies in a photo in front of the Ottawa sign.",
   "points": 200,
   "zone": 7,
   "link": "https://maps.google.com/?cid=6146839926272358918",
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
        
        .card {
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .card-curse {
            border-color: #ff4444;
            background: #fff5f5;
        }
        
        .card-advantage {
            border-color: #44ff44;
            background: #f5fff5;
        }
        
        .card-trivia {
            border-color: #4444ff;
            background: #f5f5ff;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h1 style='text-align: center; color: blue;'>LITs' Ottawa Game</h1>", unsafe_allow_html=True)

gdf = gpd.read_file(os.path.join(os.getcwd(), "data", "zones.kml"), driver="KML")

if "team" not in st.session_state:
    st.session_state.team = None
if "game_id" not in st.session_state:
    st.session_state.game_id = None
if "last_clicked_challenge" not in st.session_state:
    st.session_state.last_clicked_challenge = None
if "confirming_deposit" not in st.session_state:
    st.session_state.confirming_deposit = False
if "confirming_challenge" not in st.session_state:
    st.session_state.confirming_challenge = False
if "deposit_amount_to_confirm" not in st.session_state:
    st.session_state.deposit_amount_to_confirm = 0
if "confirming_card_use" not in st.session_state:
    st.session_state.confirming_card_use = None
if "curse_acknowledgment_needed" not in st.session_state:
    st.session_state.curse_acknowledgment_needed = None
if "trivia_wager" not in st.session_state:
    st.session_state.trivia_wager = 0
if "trivia_question_active" not in st.session_state:
    st.session_state.trivia_question_active = None
if "input_submitted" not in st.session_state:
    st.session_state.input_submitted = False
if "clearing_curse" not in st.session_state:
    st.session_state.clearing_curse = None
if "showing_curse_input" not in st.session_state:
    st.session_state.showing_curse_input = None

if st.session_state.team == None or st.session_state.game_id == None:
    game_id = st.text_input("Enter your game ID:", key="game_id_input", placeholder="Enter your game ID here")
    team = st.radio("Team:", ["Orange", "Pink"], key="team_radio", horizontal=True)
    
    if st.button("Go!") and team and game_id:
        st.session_state.team = team.lower()
        st.session_state.game_id = game_id
        st.session_state.getting_location = True  # Request location immediately
        
        # Test connection with better error handling
        with st.spinner("Connecting to database..."):
            client, error = test_mongo_connection()
            
        if client is None:
            st.error(f"Database connection failed: {error}")
            st.info("**Troubleshooting steps:**")
            st.info("1. **Check MongoDB Atlas IP whitelist** - Go to Network Access → Add IP Address → Allow Access from Anywhere (0.0.0.0/0)")
            st.info("2. **Check your internet connection**")
            st.info("3. **Try refreshing the page**")
            st.info("4. **Try a different network (mobile hotspot)**")
            st.info("5. **Contact support if the issue persists**")
            
            if st.button("🔄 Retry Connection"):
                st.rerun()
        else:
            try:
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
                        # Add card-related fields
                        team_data["hand"] = []
                        team_data["drawn_cards"] = []
                        team_data["active_curses"] = []
                        team_data["gold_rush_active"] = False
                        team_documents.append(team_data)
                    
                    # Insert all team documents
                    collection.insert_many(team_documents)
                
                st.session_state.zoom = 14
                st.success("✅ Connected successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Database initialization failed: {e}")

else:
    # For the main game logic, also use better error handling
    try:
        client, error = test_mongo_connection()
        if client is None:
            st.error(f"🚨 Database connection lost: {error}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Retry Connection"):
                    st.rerun()
            with col2:
                if st.button("🏠 Back to Start"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
            st.stop()
            
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

    except Exception as e:
        st.error(f"Critical database error: {e}")
        if st.button("🔄 Reset and Try Again"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        st.stop()

    # Get current team data
    current_team_data = orange_data if st.session_state.team == "orange" else pink_data
    other_team = "pink" if st.session_state.team == "orange" else "orange"
    other_team_data = pink_data if st.session_state.team == "orange" else orange_data

    # Check for curse acknowledgment needed
    if current_team_data and current_team_data.get("active_curses"):
        for curse in current_team_data["active_curses"]:
            if not curse.get("acknowledged", False):
                st.session_state.curse_acknowledgment_needed = curse
                break

    # Show curse acknowledgment popup if needed
    if st.session_state.curse_acknowledgment_needed:
        curse = st.session_state.curse_acknowledgment_needed
        st.error("🚨 **CURSE RECEIVED!** 🚨")
        st.markdown(f"### {curse['title']}")
        st.write(curse['description'])
        if curse.get('link'):
            st.write(f"Link: {curse['link']}")
        if curse.get('value'):
            st.write(f"Required value: {curse['value']}")
        
        # Check if this is an auto-clearing curse
        if curse.get('auto_clear', False):
            if st.button("Acknowledge (Curse will be cleared)", type="primary"):
                # Remove curse immediately after acknowledgment
                collection.update_one(
                    {"_id": st.session_state.team},
                    {"$pull": {"active_curses": {"title": curse["title"]}}}
                )
                collection.update_one(
                    {"_id": other_team},
                    {"$push": {"notifications": f"The {st.session_state.team} team has acknowledged the curse: {curse['title']}"}}
                )
                st.session_state.curse_acknowledgment_needed = None
                st.rerun()
        else:
            if st.button("Acknowledge Curse", type="primary"):
                # Mark curse as acknowledged
                collection.update_one(
                    {"_id": st.session_state.team, "active_curses.title": curse["title"]},
                    {"$set": {"active_curses.$.acknowledged": True}}
                )
                st.session_state.curse_acknowledgment_needed = None
                st.rerun()
        st.stop()

    # Check if team is cursed (and acknowledged)
    is_cursed = current_team_data and any(
        curse.get("acknowledged", False) for curse in current_team_data.get("active_curses", [])
    )

    if is_cursed:
        st.error("🚨 **CURSED!** 🚨")
        
        # Check if we're in curse clearing confirmation mode
        if st.session_state.clearing_curse:
            curse = st.session_state.clearing_curse
            st.markdown("---")
            st.markdown("### 🔔 Confirm Curse Clearing")
            st.write(f"**Curse:** {curse['title']}")
            st.write(f"**Description:** {curse['description']}")
            if curse.get('value'):
                st.write(f"**Required value:** {curse['value']}")
            st.write("Are you sure you have completed this curse?")
            
            col_cancel, col_confirm = st.columns(2)
            with col_cancel:
                if st.button("❌ Cancel Clearing", type="secondary", key="cancel_curse_clear"):
                    st.session_state.clearing_curse = None
                    st.rerun()
            with col_confirm:
                if st.button("✅ Confirm Curse Cleared", type="primary", key="confirm_curse_clear"):
                    # Remove curse and notify cursed team
                    collection.update_one(
                        {"_id": st.session_state.team},
                        {"$pull": {"active_curses": {"title": curse["title"]}}}
                    )
                    collection.update_one(
                        {"_id": other_team},
                        {"$push": {"notifications": f"The {st.session_state.team} team has cleared the curse: {curse['title']}"}}
                    )
                    st.success("Curse cleared!")
                    st.session_state.clearing_curse = None
                    st.rerun()
            st.markdown("---")
        else:
            # Show active curses and clear buttons
            for curse in current_team_data.get("active_curses", []):
                if curse.get("acknowledged", False):
                    st.markdown(f"**{curse['title']}**")
                    st.write(curse['description'])
                    if curse.get('link'):
                        st.write(f"Link: {curse['link']}")
                    if curse.get('value'):
                        st.write(f"Required value: {curse['value']}")
                    
                    if st.button(f"Clear {curse['title']}", key=f"clear_{curse['title']}"):
                        st.session_state.clearing_curse = curse
                        st.rerun()
                    st.markdown("---")

    if "lat" not in st.session_state:
        st.session_state.lat = None
    if "lon" not in st.session_state:
        st.session_state.lon = None
    if "zoom" not in st.session_state:
        st.session_state.zoom = 14

    # Show location loading message if getting location
    if st.session_state.get("getting_location", False) and (st.session_state.lat is None or st.session_state.lon is None):
        st.info("🌍 Getting your location... Please allow location access when prompted.")
        st.info("If location access is denied, you can still play but will need to manually update your location using the ✛ button.")
        
        # Try to get location immediately
        try:
            loc = get_geolocation()
            if loc and "coords" in loc:
                st.session_state.lat = loc["coords"]["latitude"]
                st.session_state.lon = loc["coords"]["longitude"]
                st.session_state.getting_location = False
                st.success("📍 Location obtained!")
                st.rerun()
        except (TypeError, KeyError):
            # Location not available yet, keep trying
            pass

    m = folium.Map(
        min_zoom=5,
        location=[centre["lat"], centre["lon"]],  # Always center on Ottawa initially
        zoom_start=14,
    )

    # Only show location marker if we have real coordinates
    if st.session_state.lat is not None and st.session_state.lon is not None:
        folium.Marker(
            location=[st.session_state.lat, st.session_state.lon],
            icon=folium.DivIcon(
                html=f'<i class="fa fa-location-crosshairs" style="color: #0050ff; font-size: 20px;"></i>',
                icon_size=(25, 25),
                icon_anchor=(12.5, 12.5)
            )
        ).add_to(m)

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
            locations=coords,
            color=zone_color,
            fill=True,
            fill_opacity=fill_opacity,
            weight=border_weight,
            popup=folium.Popup(popup_html, max_width=200)
        ).add_to(m)

    # Get completed challenges for current team
    completed_challenges = current_team_data.get("completed_challenges", []) if current_team_data else []
    
    # Only show challenges that haven't been completed by this team
    for i, challenge in enumerate(challenges):
        if challenge["title"] not in completed_challenges:
            folium.Marker(
                location=[challenge["lat"], challenge["lon"]],
                icon=folium.DivIcon(
                    html=f'<i class="fa-solid fa-trophy" style="color: #{"FFD700" if challenge["points"] >= 300 else "C0C0C0" if challenge["points"] >= 200 else "CD7F32"}; font-size: 25px;"></i>',
                    icon_size=(24, 16),
                    icon_anchor=(12, 8)
                ),
                popup=folium.Popup(
                    f"""<b style="text-align: center;"><h3>{challenge['location']}</h3>{challenge['title']}</b><br><i>Points: {challenge['points']}</i><br>{challenge['challenge']}<br><a href='{challenge['link']}' target='_blank'>View on Google Maps</a>""",
                    max_width=300,
                ),
            ).add_to(m)
        
    folium.TileLayer(
            tiles='https://api.maptiler.com/maps/voyager/{z}/{x}/{y}.png?key=' + st.secrets["map_tiler"],
            attr='<a href="https://www.maptiler.com/copyright/" target="_blank">&copy; MapTiler</a>',
            api_key=st.secrets["map_tiler"],
            min_zoom=13,
            max_zoom=21,
        ).add_to(m)

    map_container = st.container()
    with map_container:
        output = st_folium(
            m,
            height=400,
            width=None,
        )

    # Check if a challenge marker was clicked
    if output["last_object_clicked_popup"] is not None:
        popup_content = output["last_object_clicked_popup"]
        # Find which challenge was clicked based on popup content
        for challenge in challenges:
            if challenge["title"] in popup_content and challenge["title"] not in completed_challenges:
                st.session_state.last_clicked_challenge = challenge
                break

    # Display team info and deposit interface (only if not cursed)
    if orange_data and pink_data and not is_cursed:
        team_color = "#FF9600" if st.session_state.team == "orange" else "#FF0096"
        team_emoji = "🧡" if st.session_state.team == "orange" else "🩷"
        
        st.markdown(f"<h4 style='color: {team_color}; text-align: center;'>{team_emoji} {st.session_state.team.title()} Team {team_emoji}</h4>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='color: {team_color}; text-align: center;'>Balance: {current_team_data.get('balance', 0)} points</h4>", unsafe_allow_html=True)
        
        # Check if we're in confirmation mode for deposit
        if st.session_state.confirming_deposit:
            st.markdown("---")
            st.markdown("### 🔔 Confirm Point Deposit")
            st.write(f"**Zone:** {nearest_zone}")
            st.write(f"**Points to deposit:** {st.session_state.deposit_amount_to_confirm}")
            st.write(f"**Your current balance:** {current_team_data.get('balance', 0)} points")
            st.write(f"**Balance after deposit:** {current_team_data.get('balance', 0) - st.session_state.deposit_amount_to_confirm} points")
            st.write("Are you sure you want to deposit these points?")
            
            col_cancel, col_confirm = st.columns(2)
            with col_cancel:
                if st.button("❌ Cancel", type="secondary"):
                    st.session_state.confirming_deposit = False
                    st.session_state.deposit_amount_to_confirm = 0
                    st.rerun()
            with col_confirm:
                if st.button("✅ Confirm Deposit", type="primary"):
                    try:
                        # Update database
                        collection.update_one(
                            {"_id": st.session_state.team},
                            {
                                "$inc": {
                                    "balance": -st.session_state.deposit_amount_to_confirm,
                                    f"zone_{nearest_zone}": st.session_state.deposit_amount_to_confirm
                                }
                            }
                        )
                        st.success(f"Successfully deposited {st.session_state.deposit_amount_to_confirm} points to Zone {nearest_zone}!")
                        st.session_state.confirming_deposit = False
                        st.session_state.deposit_amount_to_confirm = 0
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error depositing points: {e}")
            st.markdown("---")
        else:
            if nearest_zone is not None:
                col1, col2 = st.columns(2)
                with col1:
                    max_deposit = current_team_data.get('balance', 0)
                    deposit_amount = st.number_input("How many points do you want to deposit:", min_value=0, max_value=max_deposit, value=0)
                with col2:
                    if st.button(f"Deposit to Zone {nearest_zone}"):
                        if deposit_amount > 0:
                            st.session_state.confirming_deposit = True
                            st.session_state.deposit_amount_to_confirm = deposit_amount
                            st.rerun()
                        else:
                            st.warning("Please enter a deposit amount greater than 0.")
            else:
                if st.session_state.lat is None or st.session_state.lon is None:
                    st.warning("🌍 Waiting for location... Click the ✛ button to manually update your location.")
                else:
                    st.warning("Please enable location services to deposit points.")

    # Check if we're in confirmation mode for challenge
    if st.session_state.confirming_challenge and st.session_state.last_clicked_challenge is not None:
        challenge = st.session_state.last_clicked_challenge
        st.markdown("---")
        st.markdown("### 🏆 Confirm Challenge Completion")
        st.write(f"**Challenge:** {challenge['title']}")
        
        # Check if gold rush is active
        gold_rush_multiplier = 1.5 if current_team_data.get("gold_rush_active", False) else 1
        points_to_award = int(challenge['points'] * gold_rush_multiplier)
        
        st.write(f"**Points:** {challenge['points']}")
        if gold_rush_multiplier > 1:
            st.write(f"**Gold Rush Bonus:** {points_to_award} points (1.5x multiplier!)")
        st.write(f"**Location:** {challenge['location']}")
        st.write(f"**Your current balance:** {current_team_data.get('balance', 0)} points")
        st.write(f"**Balance after completion:** {current_team_data.get('balance', 0) + points_to_award} points")
        st.write("**Challenge Description:**")
        st.write(challenge['challenge'])
        st.write("Are you sure you have completed this challenge?")
        
        col_cancel, col_confirm = st.columns(2)
        with col_cancel:
            if st.button("❌ Cancel Challenge", type="secondary"):
                st.session_state.confirming_challenge = False
                st.rerun()
        with col_confirm:
            if st.button("✅ Confirm Completion", type="primary"):
                try:
                    # Update database - add points to balance and mark challenge as completed
                    update_dict = {
                        "$inc": {"balance": points_to_award},
                        "$addToSet": {"completed_challenges": challenge['title']}
                    }
                    
                    # If gold rush was active, deactivate it
                    if current_team_data.get("gold_rush_active", False):
                        update_dict["$set"] = {"gold_rush_active": False}
                        update_dict["$pull"] = {"hand": {"title": "Advantage: You struck gold!"}}
                    
                    collection.update_one(
                        {"_id": st.session_state.team},
                        update_dict
                    )
                    success_msg = f"Challenge '{challenge['title']}' completed! +{points_to_award} points!"
                    if gold_rush_multiplier > 1:
                        success_msg += " (Gold Rush bonus applied!)"
                    st.success(success_msg)
                    st.session_state.last_clicked_challenge = None
                    st.session_state.confirming_challenge = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Error completing challenge: {e}")
        st.markdown("---")

    # Create a container for the buttons with minimal spacing (only if not cursed)
    if not is_cursed:
        button_container = st.container()
        with button_container:
            col1, col2, col3 = st.columns((1, 1, 1))  # Three equal columns
            with col1:
                if st.button("✛ Update Location ✛"):
                    st.session_state.getting_location = True
            
            with col2:
                # Challenge completion button
                if st.session_state.last_clicked_challenge is not None:
                    challenge = st.session_state.last_clicked_challenge
                    if st.button(f"Complete: {challenge['title']} ({challenge['points']} pts)"):
                        st.session_state.confirming_challenge = True
                        st.rerun()
                else:
                    st.button("🏆 Click a challenge 🏆", disabled=True)
            
            with col3:
                # Check if gold rush is active (disables card drawing)
                can_draw_card = not current_team_data.get("gold_rush_active", False)
                draw_disabled = current_team_data.get('balance', 0) < 100 or not can_draw_card
                
                button_text = "🃏 Draw a card 🃏 (100 pts)"
                if not can_draw_card:
                    button_text = "🚫 Complete challenge first 🚫"
                
                if st.button(button_text, disabled=draw_disabled):
                    # Draw a random card that hasn't been drawn yet
                    drawn_cards = current_team_data.get("drawn_cards", [])
                    available_cards = [card_id for card_id in CARDS.keys() if card_id not in drawn_cards]
                    
                    if available_cards:
                        drawn_card_id = random.choice(available_cards)
                        drawn_card = CARDS[drawn_card_id].copy()
                        drawn_card["id"] = drawn_card_id
                        
                        # Deduct cost and add card to hand
                        collection.update_one(
                            {"_id": st.session_state.team},
                            {
                                "$inc": {"balance": -100},
                                "$push": {
                                    "hand": drawn_card,
                                    "drawn_cards": drawn_card_id
                                }
                            }
                        )
                        
                        # Auto-activate advantage cards
                        if drawn_card["type"] == "advantage":
                            collection.update_one(
                                {"_id": st.session_state.team},
                                {"$set": {"gold_rush_active": True}}
                            )
                        
                        st.success(f"Drew card: {drawn_card['title']}")
                        st.rerun()
                    else:
                        st.warning("No more cards available to draw!")

    # Display hand
    if current_team_data and current_team_data.get("hand"):
        st.markdown("---")
        st.markdown("### 🃏 Your Hand")
        
        for i, card in enumerate(current_team_data["hand"]):
            card_class = "card"
            if "curse" in card["type"]:
                card_class += " card-curse"
            elif card["type"] == "advantage":
                card_class += " card-advantage"
            elif "risky" in card["type"]:
                card_class += " card-trivia"
            
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            st.markdown(f"**{card['title']}**")
            st.write(card["description"])
            if card.get("link"):
                st.write(f"[Helpful Link]({card['link']})")
            
            # Don't show use button for advantage cards (auto-activated)
            if card["type"] != "advantage":
                if st.button(f"Use {card['title']}", key=f"use_card_{i}"):
                    st.session_state.confirming_card_use = card
                    st.rerun()
            else:
                st.info("This advantage is automatically active!")
            
            st.markdown('</div>', unsafe_allow_html=True)

    # Card use confirmation
    if st.session_state.confirming_card_use:
        card = st.session_state.confirming_card_use
        st.markdown("---")
        st.markdown("### 🃏 Confirm Card Use")
        st.write(f"**Card:** {card['title']}")
        st.write(f"**Description:** {card['description']}")
        
        # Handle risky trivia cards with wagering
        if "risky" in card["type"]:
            st.write("**How much do you want to wager?**")
            max_wager = current_team_data.get('balance', 0)
            wager = st.number_input("Wager amount:", min_value=1, max_value=max_wager, value=min(100, max_wager), key="wager_input")
            
            col_cancel, col_confirm = st.columns(2)
            with col_cancel:
                if st.button("❌ Cancel Card", type="secondary"):
                    st.session_state.confirming_card_use = None
                    st.rerun()
            with col_confirm:
                if st.button("✅ Place Wager", type="primary"):
                    # Deduct wager from balance
                    collection.update_one(
                        {"_id": st.session_state.team},
                        {"$inc": {"balance": -wager}}
                    )
                    st.session_state.trivia_wager = wager
                    st.session_state.trivia_question_active = card
                    st.session_state.confirming_card_use = None
                    st.rerun()
                    
        elif card["type"] == "curse_with_input":
            # For input-based curses, move to input phase
            col_cancel, col_confirm = st.columns(2)
            with col_cancel:
                if st.button("❌ Cancel Card", type="secondary"):
                    st.session_state.confirming_card_use = None
                    st.rerun()
            with col_confirm:
                if st.button("✅ Proceed to Input", type="primary"):
                    st.session_state.showing_curse_input = card
                    st.session_state.confirming_card_use = None
                    st.rerun()
        else:
            st.write("Are you sure you want to use this card?")
            
            col_cancel, col_confirm = st.columns(2)
            with col_cancel:
                if st.button("❌ Cancel Card", type="secondary"):
                    st.session_state.confirming_card_use = None
                    st.rerun()
            with col_confirm:
                if st.button("✅ Confirm Use", type="primary"):
                    # Handle simple curse cards
                    if card["type"] == "curse":
                        # Apply curse to cursed team
                        curse_data = {
                            "title": card["title"],
                            "description": card["description"],
                            "acknowledged": False
                        }
                        if card.get("link"):
                            curse_data["link"] = card["link"]
                        if card.get("auto_clear"):
                            curse_data["auto_clear"] = True
                        
                        collection.update_one(
                            {"_id": other_team},
                            {"$push": {"active_curses": curse_data}}
                        )
                        
                        # Remove card from hand
                        collection.update_one(
                            {"_id": st.session_state.team},
                            {"$pull": {"hand": {"title": card["title"]}}}
                        )
                        st.success(f"Curse '{card['title']}' sent to {other_team} team!")
                        st.session_state.confirming_card_use = None
                        st.rerun()

    # Handle curse input phase
    if st.session_state.showing_curse_input:
        card = st.session_state.showing_curse_input
        st.markdown("---")
        st.markdown(f"### 🃏 {card['title']} - Input Required")
        st.write(f"**Description:** {card['description']}")
        
        if card["title"] == "Curse of the Luxury Car":
            st.write("Enter the minimum MSRP of your car:")
            car_price = st.number_input("Car MSRP ($):", min_value=0, step=1000, key="car_price_input")
            
            col_cancel, col_submit = st.columns(2)
            with col_cancel:
                if st.button("❌ Cancel", type="secondary"):
                    st.session_state.showing_curse_input = None
                    st.rerun()
            with col_submit:
                if st.button("✅ Send Curse", type="primary"):
                    curse_data = {
                        "title": card["title"],
                        "description": f"{card['description']} Required MSRP to beat: ${car_price:,}",
                        "value": car_price,
                        "acknowledged": False,
                        "link": card.get("link")
                    }
                    collection.update_one(
                        {"_id": other_team},
                        {"$push": {"active_curses": curse_data}}
                    )
                    collection.update_one(
                        {"_id": st.session_state.team},
                        {"$pull": {"hand": {"title": card["title"]}}}
                    )
                    st.success(f"Car curse sent! cursed team must beat ${car_price:,}")
                    st.session_state.showing_curse_input = None
                    st.rerun()
                    
        elif card["title"] == "Curse of the Cairn":
            st.write("How many rocks did you stack?")
            rock_count = st.number_input("Number of rocks:", min_value=1, max_value=50, step=1, key="rock_count_input")
            
            col_cancel, col_submit = st.columns(2)
            with col_cancel:
                if st.button("❌ Cancel", type="secondary"):
                    st.session_state.showing_curse_input = None
                    st.rerun()
            with col_submit:
                if st.button("✅ Send Curse", type="primary"):
                    curse_data = {
                        "title": card["title"],
                        "description": f"{card['description']} You must stack {rock_count} rocks to clear this curse.",
                        "value": rock_count,
                        "acknowledged": False
                    }
                    collection.update_one(
                        {"_id": other_team},
                        {"$push": {"active_curses": curse_data}}
                    )
                    collection.update_one(
                        {"_id": st.session_state.team},
                        {"$pull": {"hand": {"title": card["title"]}}}
                    )
                    st.success(f"Cairn curse sent! cursed team must stack {rock_count} rocks")
                    st.session_state.showing_curse_input = None
                    st.rerun()
                    
        elif card["title"] == "Curse of the Bird Guide":
            st.write("How many seconds did you film the bird?")
            film_time = st.number_input("Seconds filmed:", min_value=1, max_value=420, step=1, key="film_time_input")
            
            col_cancel, col_submit = st.columns(2)
            with col_cancel:
                if st.button("❌ Cancel", type="secondary"):
                    st.session_state.showing_curse_input = None
                    st.rerun()
            with col_submit:
                if st.button("✅ Send Curse", type="primary"):
                    curse_data = {
                        "title": card["title"],
                        "description": f"{card['description']} You must film a bird for more than {film_time} seconds to clear this curse.",
                        "value": film_time,
                        "acknowledged": False
                    }
                    collection.update_one(
                        {"_id": other_team},
                        {"$push": {"active_curses": curse_data}}
                    )
                    collection.update_one(
                        {"_id": st.session_state.team},
                        {"$pull": {"hand": {"title": card["title"]}}}
                    )
                    st.success(f"Bird curse sent! cursed team must film for more than {film_time} seconds")
                    st.session_state.showing_curse_input = None
                    st.rerun()

    # Trivia question handling
    if st.session_state.trivia_question_active:
        card = st.session_state.trivia_question_active
        st.markdown("---")
        st.markdown("### 🧠 Trivia Question")
        st.write(f"**Wager:** {st.session_state.trivia_wager} points")
        st.write(f"**Potential winnings:** {st.session_state.trivia_wager * 3} points")
        st.write("---")
        st.write(f"**Question:** {card['question']}")
        
        if card["type"] == "risky_trivia":
            # Geography question - number input
            answer = st.number_input("Your answer:", min_value=0, step=1, key="trivia_answer")
            if st.button("Submit Answer"):
                correct_answer = card["answer"]
                tolerance = card["tolerance"]
                is_correct = abs(answer - correct_answer) <= tolerance
                
                if is_correct:
                    # Give back wager + winnings (total = wager * 4, since we already deducted wager)
                    total_payout = st.session_state.trivia_wager * 4  # Original wager + 3x winnings
                    collection.update_one(
                        {"_id": st.session_state.team},
                        {"$inc": {"balance": total_payout}}
                    )
                    net_winnings = st.session_state.trivia_wager * 3
                    st.success(f"Correct! You won {net_winnings} points! (Answer was {correct_answer:,})")
                else:
                    st.error(f"Incorrect! You lost {st.session_state.trivia_wager} points. (Answer was {correct_answer:,})")
                
                # Remove card from hand
                collection.update_one(
                    {"_id": st.session_state.team},
                    {"$pull": {"hand": {"title": card["title"]}}}
                )
                st.session_state.trivia_question_active = None
                st.session_state.trivia_wager = 0
                st.rerun()
                
        elif card["type"] == "risky_trivia_mc":
            # Multiple choice question
            selected_answer = st.radio("Choose your answer:", card["options"], key="mc_answer")
            if st.button("Submit Answer"):
                is_correct = selected_answer == card["answer"]
                
                if is_correct:
                    # Give back wager + winnings (total = wager * 4, since we already deducted wager)
                    total_payout = st.session_state.trivia_wager * 4  # Original wager + 3x winnings
                    collection.update_one(
                        {"_id": st.session_state.team},
                        {"$inc": {"balance": total_payout}}
                    )
                    net_winnings = st.session_state.trivia_wager * 3
                    st.success(f"Correct! You won {net_winnings} points!")
                else:
                    st.error(f"Incorrect! You lost {st.session_state.trivia_wager} points. (Correct answer was: {card['answer']})")
                
                # Remove card from hand
                collection.update_one(
                    {"_id": st.session_state.team},
                    {"$pull": {"hand": {"title": card["title"]}}}
                )
                st.session_state.trivia_question_active = None
                st.session_state.trivia_wager = 0
                st.rerun()

    if "getting_location" in st.session_state and st.session_state.getting_location:
        try:
            loc = get_geolocation()
            if loc and "coords" in loc:
                st.session_state.lat = loc["coords"]["latitude"]
                st.session_state.lon = loc["coords"]["longitude"]
                st.session_state.zoom = output["zoom"]
                st.session_state.getting_location = False  # Reset flag
        except (TypeError, KeyError):
            st.warning("Unable to get location. Please enable location services and try again.")
            st.session_state.getting_location = False