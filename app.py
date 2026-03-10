import streamlit as st
import streamlit.components.v1 as components
import os
import urllib.parse
import urllib.request
import json
import re
import time
import concurrent.futures
from agno.agent import Agent
from agno.tools.serpapi import SerpApiTools
from agno.models.google import Gemini

# --- CONFIGURATION & SECRETS ---
st.set_page_config(page_title="Academic Travel Planner", layout="wide", page_icon="✈️", initial_sidebar_state="expanded")

# --- INITIALIZE SESSION STATE ---
if 'itinerary_data' not in st.session_state:
    st.session_state.itinerary_data = None
if 'dest_name' not in st.session_state:
    st.session_state.dest_name = ""
if 'trip_params' not in st.session_state:
    st.session_state.trip_params = {}
if 'celebrated' not in st.session_state:
    st.session_state.celebrated = False

# --- CUSTOM CSS FOR PREMIUM UI & PDF PRINTING ---
st.markdown("""
<style>
    /* Premium Timeline & Visual Styles */
    .stMarkdown img {
        border-radius: 16px;
        max-height: 400px;
        object-fit: cover;
        width: 100%;
        margin-bottom: 15px;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .stMarkdown img:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04);
    }
    
    /* Apply rounded corners to Main Screen Images (Gallery & Hero Banner) */
    [data-testid="stMainBlock"] [data-testid="stImage"] img {
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }

    .stMarkdown blockquote {
        border-left: 6px solid #FF4B4B; 
        background: linear-gradient(90deg, rgba(255, 75, 75, 0.08) 0%, rgba(255, 255, 255, 0) 100%);
        padding: 16px 20px;
        border-radius: 0 12px 12px 0;
        font-size: 1.05em;
        font-weight: 500;
        margin: 25px 0 25px 20px;
        color: #4A4A4A;
    }
    .stMarkdown h2 { 
        color: #1E293B; 
        border-bottom: 3px solid #F1F5F9; 
        padding-bottom: 10px; 
        margin-top: 30px;
        font-weight: 800;
    }
    .stMarkdown h3 { 
        color: #2563EB; 
        padding-top: 15px; 
        font-weight: 700;
    }
    
    /* Make Metric Cards pop */
    div[data-testid="metric-container"] {
        background-color: rgba(241, 245, 249, 0.5);
        border: 1px solid #e2e8f0;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* 🖨️ PRINT TO PDF STYLES */
    @media print {
        header, footer, [data-testid="stSidebar"], .stButton, iframe, [data-testid="stStatusWidget"] {
            display: none !important;
        }
        .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown li, .stMarkdown blockquote {
            color: black !important;
        }
        img { page-break-inside: avoid; border-radius: 8px; box-shadow: none; }
        blockquote { page-break-inside: avoid; border-left: 4px solid black; background: #f9f9f9; }
    }
</style>
""", unsafe_allow_html=True)

# 👇 PASTE YOUR NEW TIER 1 KEY INSIDE THE QUOTATION MARKS BELOW 👇
LOCAL_SERPAPI_KEY = "" 
LOCAL_GOOGLE_KEY = "" 
# 👆 ------------------------------------------------ 👆

try:
    SYSTEM_SERPAPI_KEY = st.secrets["SERPAPI_KEY"] 
    SYSTEM_GOOGLE_KEY = st.secrets["GOOGLE_API_KEY"] 
except Exception:
    SYSTEM_SERPAPI_KEY = LOCAL_SERPAPI_KEY
    SYSTEM_GOOGLE_KEY = LOCAL_GOOGLE_KEY

# Set the active API key for the environment
os.environ["GOOGLE_API_KEY"] = SYSTEM_GOOGLE_KEY

# --- REAL PHOTO FETCHING ENGINE ---
def fetch_real_image(query):
    """Fetches real photos from Wikipedia API (Free) or falls back to Pollinations."""
    try:
        # Step 1: Search Wikipedia for the location
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&utf8=&format=json"
        req = urllib.request.Request(search_url, headers={'User-Agent': 'TravelPlannerApp/1.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            search_data = json.loads(response.read().decode())
            if not search_data['query']['search']:
                raise ValueError("No Wikipedia page found")
            title = search_data['query']['search'][0]['title']
            
        # Step 2: Grab the main verified photo of that page
        image_url = f"https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=pageimages&format=json&pithumbsize=1000"
        req = urllib.request.Request(image_url, headers={'User-Agent': 'TravelPlannerApp/1.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            image_data = json.loads(response.read().decode())
            pages = image_data['query']['pages']
            page_id = list(pages.keys())[0]
            if 'thumbnail' in pages[page_id]:
                return pages[page_id]['thumbnail']['source']
    except Exception:
        pass
    
    # Fallback to realistic AI image if Wikipedia lacks a photo
    return f"https://image.pollinations.ai/prompt/Realistic+Cinematic+Photography+of+{urllib.parse.quote(query)}?width=1000&height=500"

def process_images(text):
    """Finds all [REAL_IMG] placeholders from the AI and concurrently injects real photos."""
    pattern = r"\[REAL_IMG:\s*(.*?)\]"
    matches = list(set(re.findall(pattern, text)))
    
    if not matches:
        return text
        
    def get_img_url(query):
        return query, fetch_real_image(query)

    # Fetch all images simultaneously to keep the app lightning fast
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(get_img_url, matches)
        
    for query, url in results:
        text = text.replace(f"[REAL_IMG: {query}]", url)
        
    return text

# --- SIDEBAR: DASHBOARD LAYOUT ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png", width=50)
    st.markdown("### ⚙️ Trip Configuration")
    
    destination = st.text_input("🛬 Destination:", "")
    
    col1, col2 = st.columns(2)
    with col1:
        num_days = st.number_input("📅 Days:", min_value=1, max_value=14, value=4)
    with col2:
        travel_month = st.selectbox("🗓️ Month:", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], index=2)
        
    traveler_persona = st.selectbox("👥 Persona:", ["Solo Independent Traveler", "Couple / DINKs", "Family with Young Children", "Seniors / Retirees", "Student Group"])
    budget = st.select_slider("💰 Budget Level:", options=["Budget/Backpacker", "Mid-Range", "Luxury/Boutique"], value="Mid-Range")
    
    user_preferences = st.text_area(
        "✍️ Custom Preferences:",
        placeholder="Enter your preferences...",
        height=120
    )
    
    st.markdown("---")
    generate_btn = st.button("✨ Generate Premium Itinerary", use_container_width=True, type="primary")

# --- INPUT VALIDATION & STATE RESET ---
if generate_btn:
    if not destination.strip():
        st.sidebar.warning("⚠️ Please enter a destination.")
        st.stop()
    if not SYSTEM_GOOGLE_KEY:
        st.sidebar.error("🚨 API Key missing!")
        st.stop()
        
    # Clear old data and prepare for new generation
    st.session_state.itinerary_data = None
    st.session_state.celebrated = False
    st.session_state.dest_name = destination
    st.session_state.trip_params = {
        "days": num_days,
        "month": travel_month,
        "budget": budget,
        "persona": traveler_persona
    }

# --- MAIN SCREEN AREA ---

# Empty State: Inspiration Gallery
if not generate_btn and not st.session_state.itinerary_data:
    st.markdown('<h1 style="text-align: center; font-size: 3.5rem; font-weight: 900; margin-bottom: 0;">🌍 Destination Design Lab</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.3rem; color: #64748b; margin-bottom: 40px;">Design your perfect travel itinerary</p>', unsafe_allow_html=True)
    
    st.info("👈 Use the Dashboard on the left to configure your parameters and generate a custom AI dossier!")
    
    st.markdown("### ✨ Inspiration Gallery")
    gal1, gal2, gal3 = st.columns(3)
    
    with gal1:
        st.image("https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=600&h=400&q=80", use_container_width=True)
        st.markdown("#### 🗼 Tokyo, Japan")
        st.caption("Neon lights, ancient temples, and culinary perfection.")
    with gal2:
        st.image("https://images.unsplash.com/photo-1499856871958-5b9627545d1a?auto=format&fit=crop&w=600&h=400&q=80", use_container_width=True)
        st.markdown("#### 🥐 Paris, France")
        st.caption("Art, romance, and café culture by the Seine.")
    with gal3:
        st.image("https://images.unsplash.com/photo-1550236520-7050f3582da0?auto=format&fit=crop&w=600&h=400&q=80", use_container_width=True)
        st.markdown("#### 🏔️ Banff, Canada")
        st.caption("Crystal lakes, towering peaks, and ultimate wilderness.")

# Active State: Generating or Displaying Results
if generate_btn or st.session_state.itinerary_data:
    
    # Grab active params (either currently generating, or saved in memory)
    disp_dest = destination if generate_btn else st.session_state.dest_name
    disp_days = num_days if generate_btn else st.session_state.trip_params["days"]
    disp_month = travel_month if generate_btn else st.session_state.trip_params["month"]
    disp_budget = budget if generate_btn else st.session_state.trip_params["budget"]
    disp_persona = traveler_persona if generate_btn else st.session_state.trip_params["persona"]

    st.markdown(f'<h1 style="text-align: center; font-size: 3rem; font-weight: 900;">{disp_dest.upper()}</h1>', unsafe_allow_html=True)
    
    # Hero Banner
    safe_dest = urllib.parse.quote(disp_dest)
    st.image(f"https://image.pollinations.ai/prompt/Beautiful+Cinematic+Landscape+Photography+of+{safe_dest}?width=1200&height=350", use_container_width=True)
    
    # Trip Summary Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📍 Destination", disp_dest)
    m2.metric("🗓️ Duration", f"{disp_days} Days ({disp_month})")
    m3.metric("💰 Budget", disp_budget)
    m4.metric("👥 Persona", disp_persona)
    
    st.markdown("---")

    # --- PHASE: GENERATION LOOP ---
    if generate_btn:
        with st.status("🤖 **Gemini 3 Flash is researching in parallel...**", expanded=True) as status:
            
            fallback_models = [
                "gemini-3-flash-preview",        
                "gemini-3.1-flash-lite-preview", 
                "gemini-2.5-flash",              
                "gemma-3-27b-it"                 
            ]
            
            success = False
            raw_content = ""
            last_error = ""
            
            for model_id in fallback_models:
                try:
                    st.write(f"⚙️ Initializing High-Speed Engine: `{model_id}`...")
                    
                    agent_tools = []
                    if "gemma" not in model_id and SYSTEM_SERPAPI_KEY:
                        agent_tools = [SerpApiTools(api_key=SYSTEM_SERPAPI_KEY)]
                    
                    # --- DEFINE PARALLEL FUNCTIONS ---
                    def get_itinerary():
                        agent = Agent(
                            name="Itinerary Planner",
                            model=Gemini(id=model_id),
                            tools=agent_tools,
                            instructions=[
                                f"You are the Itinerary Planner for a {num_days}-day trip to {destination} in {travel_month}.",
                                f"Traveler: '{traveler_persona}'. Budget: '{budget}'. Preferences: '{user_preferences}'.",
                                "Generate ONLY the day-by-day schedule. Group locations geographically.",
                                "Break each day into Morning, Afternoon, and Evening.",
                                "For EVERY single location or restaurant, you MUST use this exact layout:",
                                "### 📍 [Name of Location]",
                                "**⏱️ Suggested Time:** [e.g., 2 hours] | **[🗺️ View on Google Maps](https://www.google.com/maps/search/?api=1&query=Location+Name)**",
                                "<br><br>",
                                "<img src=\"[REAL_IMG: Location Name, City]\">",
                                "<br><br>",
                                "*Write a short, engaging description.*",
                                "> 🚊 **Transit to next location:** [e.g., 15 mins by subway/bus] | **Route:** From [Nearest Station/Stop of CURRENT location] to [Nearest Station/Stop of NEXT location]",
                                "CRITICAL IMAGE RULE: You MUST use the exact syntax <img src=\"[REAL_IMG: Location Name, City]\"> for images."
                            ]
                        )
                        return agent.run(f"Create the day-by-day itinerary for {destination}.", stream=False).content

                    def get_logistics():
                        agent = Agent(
                            name="Logistics Expert",
                            model=Gemini(id=model_id),
                            tools=agent_tools,
                            instructions=[
                                f"You are the Logistics Expert for a trip to {destination} in {travel_month}.",
                                "Generate ONLY practical logistics and local rules.",
                                "Use these exact bullet points:",
                                "- **Flight & Airports:** Major entry points.",
                                "- **Weather:** What to pack for this month.",
                                "- **Transport:** Best way to get around.",
                                "- **Etiquette:** 3 local rules to respect."
                            ]
                        )
                        return agent.run(f"Gather logistics for {destination}.", stream=False).content

                    def get_hotels(itin_text):
                        agent = Agent(
                            name="Hotel Concierge",
                            model=Gemini(id=model_id),
                            tools=agent_tools,
                            instructions=[
                                f"You are the Hotel Concierge for a trip to {destination}.",
                                f"Traveler: '{traveler_persona}'. Budget: '{budget}'. Preferences: '{user_preferences}'.",
                                "Generate ONLY 3 highly-rated hotel recommendations based on the provided itinerary.",
                                "For EVERY hotel, you MUST use this exact layout:",
                                "### 🏨 [Hotel Name]",
                                "**[🗺️ View on Google Maps](https://www.google.com/maps/search/?api=1&query=Hotel+Name)**",
                                "<br><br>",
                                "<img src=\"[REAL_IMG: Hotel Name, City]\">",
                                "<br><br>",
                                "*Write a short explanation of why this fits the user.*",
                                "CRITICAL IMAGE RULE: You MUST use the exact syntax <img src=\"[REAL_IMG: Hotel Name, City]\"> for images."
                            ]
                        )
                        return agent.run(f"Find 3 highly-rated hotels in {destination} that are geographically convenient based on this itinerary:\n\n{itin_text}", stream=False).content

                    def get_editor(itin_text):
                        agent = Agent(
                            name="Chief Editor",
                            model=Gemini(id=model_id),
                            instructions=[
                                f"You are the Chief Editor finalizing a travel plan for a {traveler_persona} traveling to {destination}.",
                                f"Their budget is {budget} and their preferences are: '{user_preferences}'.",
                                "Write a short, engaging, 1-paragraph 'Executive Welcome' that personally addresses the traveler and summarizes why this itinerary is perfect for them."
                            ]
                        )
                        return agent.run(f"Write the Executive Welcome based on this itinerary: {itin_text}", stream=False).content

                    # --- EXECUTE IN PARALLEL THREADS ---
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        st.write("🚀 **Phase 1:** Planning Itinerary & Logistics simultaneously...")
                        future_itin = executor.submit(get_itinerary)
                        future_logistics = executor.submit(get_logistics)
                        
                        itinerary_content = future_itin.result()
                        logistics_content = future_logistics.result()
                        
                        st.write("🚀 **Phase 2:** Scouting Hotels & Writing Welcome simultaneously...")
                        future_hotel = executor.submit(get_hotels, itinerary_content)
                        future_editor = executor.submit(get_editor, itinerary_content)
                        
                        hotel_content = future_hotel.result()
                        summary_content = future_editor.result()
                        
                        st.write("📸 **Phase 3:** Fetching Real Verified Photography...")
                        future_itin_img = executor.submit(process_images, itinerary_content)
                        future_hotel_img = executor.submit(process_images, hotel_content)
                        
                        itinerary_content = future_itin_img.result()
                        hotel_content = future_hotel_img.result()

                    # --- PYTHON TAB COMPILER ---
                    raw_content = f"### 📝 Editor's Welcome\n{summary_content}\n\n{itinerary_content}\n\n" \
                                  f"---TAB_SEPARATOR---\n\n" \
                                  f"## 🏨 Part 2: Top Accommodation Picks\n{hotel_content}\n\n" \
                                  f"---TAB_SEPARATOR---\n\n" \
                                  f"## 🛂 Part 3: Logistics & Practicalities\n{logistics_content}"
                    
                    success = True
                    break # Break out of the fallback loop if successful!
                    
                except Exception as e:
                    last_error = str(e)
                    st.write(f"⚠️ `{model_id}` error. Switching to next engine...")
                    time.sleep(1)
                    continue
                    
            if success:
                st.session_state.itinerary_data = raw_content
                st.rerun() # This instantly refreshes the page, skipping the loading box completely!
            else:
                status.update(label="❌ **Generation Failed**", state="error", expanded=True)
                st.error("🚨 All available AI engines have hit their daily limit.")
                st.info("💡 **Solution:** Please try again tomorrow after your quota resets.")
                st.code(f"Technical Error Data: {last_error}")

    # --- PHASE: DISPLAY RESULTS ---
    elif st.session_state.itinerary_data:
        
        # Celebratory Animations (Only run once per generation)
        if not st.session_state.celebrated:
            st.balloons()
            st.toast('Your custom itinerary has been successfully generated!', icon='🎉')
            st.session_state.celebrated = True
        
        # Tabbed Navigation (Automatically defaults to Tab 1: Itinerary)
        parts = st.session_state.itinerary_data.split("---TAB_SEPARATOR---")
        
        if len(parts) >= 3:
            tab1, tab2, tab3 = st.tabs(["🗺️ Day-by-Day Itinerary", "🏨 Accommodations", "🛂 Logistics & Practicalities"])
            with tab1:
                st.markdown(parts[0], unsafe_allow_html=True)
            with tab2:
                st.markdown(parts[1], unsafe_allow_html=True)
            with tab3:
                st.markdown(parts[2], unsafe_allow_html=True)
        else:
            st.warning("Could not automatically separate the tabs. Displaying full dossier below:")
            st.markdown(st.session_state.itinerary_data, unsafe_allow_html=True)
        
        # --- DOWNLOAD & PDF EXPORT BUTTONS ---
        st.markdown("---")
        colA, colB = st.columns(2)
        
        with colA:
            st.download_button(
                label="📄 Download Raw Markdown (.md)",
                data=st.session_state.itinerary_data.replace("---TAB_SEPARATOR---", "\n\n---\n\n"),
                file_name=f"Custom_Itinerary_{disp_dest.replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True
            )
            
        with colB:
            components.html(
                """
                <script>
                function printPage() {
                    window.parent.print();
                }
                </script>
                <button onclick="printPage()" style="width: 100%; padding: 0.5rem 1rem; background-color: #ffffff; border: 1px solid rgba(49, 51, 63, 0.2); border-radius: 0.5rem; color: #31333F; font-family: 'Source Sans Pro', sans-serif; font-size: 1rem; cursor: pointer; transition: all 0.2s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    🖨️ Save as PDF
                </button>
                <style>
                    button:hover {
                        border-color: #ff4b4b !important;
                        color: #ff4b4b !important;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }
                </style>
                """,
                height=50
            )
