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

# --- OPTION 1: ADAPTIVE GLASSMORPHISM CSS ---
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
        box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2), 0 10px 10px -5px rgba(0,0,0,0.1);
    }
    
    [data-testid="stMainBlock"] [data-testid="stImage"] img {
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }

    .stMarkdown blockquote {
        border-left: 6px solid #FF4B4B; 
        background: linear-gradient(90deg, rgba(255, 75, 75, 0.1) 0%, rgba(255, 255, 255, 0) 100%);
        padding: 16px 20px;
        border-radius: 0 12px 12px 0;
        font-size: 1.05em;
        font-weight: 500;
        margin: 25px 0 25px 20px;
    }
    .stMarkdown h2 { 
        border-bottom: 2px solid rgba(128, 128, 128, 0.2); 
        padding-bottom: 10px; 
        margin-top: 30px;
        font-weight: 800;
    }
    .stMarkdown h3 { 
        color: #2563EB; 
        padding-top: 15px; 
        font-weight: 700;
    }
    
    /* GLASSMORPHISM: Make Metric Cards pop in Light & Dark Mode */
    div[data-testid="metric-container"] {
        background: rgba(128, 128, 128, 0.05);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.05);
    }

    /* MODERN ACCORDIONS (Option 3) */
    [data-testid="stExpander"] {
        background: rgba(128, 128, 128, 0.02);
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.02);
        margin-bottom: 15px;
    }
    [data-testid="stExpander"] details summary p {
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        color: #2563EB !important;
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

# 👇 LOCAL TESTING KEYS (Keep empty if using Streamlit Secrets) 👇
LOCAL_SERPAPI_KEY = "" 
LOCAL_GOOGLE_KEY = "" 
LOCAL_UNSPLASH_KEY = ""
# 👆 -------------------------------------------------------- 👆

try:
    SYSTEM_SERPAPI_KEY = st.secrets["SERPAPI_KEY"] 
    SYSTEM_GOOGLE_KEY = st.secrets["GOOGLE_API_KEY"] 
    SYSTEM_UNSPLASH_KEY = st.secrets.get("UNSPLASH_API_KEY", "")
except Exception:
    SYSTEM_SERPAPI_KEY = LOCAL_SERPAPI_KEY
    SYSTEM_GOOGLE_KEY = LOCAL_GOOGLE_KEY
    SYSTEM_UNSPLASH_KEY = LOCAL_UNSPLASH_KEY

os.environ["GOOGLE_API_KEY"] = SYSTEM_GOOGLE_KEY

# --- THE ULTIMATE WATERFALL IMAGE ENGINE ---
def fetch_real_image(query):
    """4-Tier Image Fetcher: Unsplash -> Smart Wikipedia -> SerpApi (Google Images) -> AI Failsafe"""
    encoded_query = urllib.parse.quote(query)
    
    # TIER 1: Unsplash (Cinematic & Free)
    if SYSTEM_UNSPLASH_KEY:
        try:
            url = f"https://api.unsplash.com/search/photos?query={encoded_query}&client_id={SYSTEM_UNSPLASH_KEY}&per_page=1&orientation=landscape"
            req = urllib.request.Request(url, headers={'User-Agent': 'TravelPlanner/1.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                if data['results']:
                    return data['results'][0]['urls']['regular']
        except Exception:
            pass

    # TIER 2: Smart Wikipedia Filter (Rejects maps and logos)
    try:
        clean_query = query.split(',')[0].strip() # Removes city name to prevent wiki confusion
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_query)}&utf8=&format=json"
        req = urllib.request.Request(search_url, headers={'User-Agent': 'TravelPlanner/1.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            search_data = json.loads(response.read().decode())
            if search_data['query']['search']:
                title = search_data['query']['search'][0]['title']
                image_url = f"https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=pageimages&format=json&pithumbsize=1000"
                
                req2 = urllib.request.Request(image_url, headers={'User-Agent': 'TravelPlanner/1.0'})
                with urllib.request.urlopen(req2, timeout=3) as response2:
                    image_data = json.loads(response2.read().decode())
                    pages = image_data['query']['pages']
                    page_id = list(pages.keys())[0]
                    if 'thumbnail' in pages[page_id]:
                        img_src = pages[page_id]['thumbnail']['source']
                        # SMART FILTER: Reject if it is a map, flag, logo, or icon
                        lower_src = img_src.lower()
                        if not any(bad_word in lower_src for bad_word in ['map', 'flag', 'logo', '.svg', 'icon']):
                            return img_src
    except Exception:
        pass

    # TIER 3: SerpApi Google Images (Pinpoint Accuracy for Restaurants/Specifics)
    if SYSTEM_SERPAPI_KEY:
        try:
            url = f"https://serpapi.com/search.json?engine=google_images&q={encoded_query}&api_key={SYSTEM_SERPAPI_KEY}"
            req = urllib.request.Request(url, headers={'User-Agent': 'TravelPlanner/1.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                if 'images_results' in data and len(data['images_results']) > 0:
                    return data['images_results'][0]['original']
        except Exception:
            pass
    
    # TIER 4: Pollinations AI (Failsafe Placeholder)
    return f"https://image.pollinations.ai/prompt/Realistic+Cinematic+Photography+of+{encoded_query}?width=1000&height=500"


def process_images(text):
    """Finds all [REAL_IMG] placeholders and concurrently runs the Waterfall Engine."""
    pattern = r"\[REAL_IMG:\s*(.*?)\]"
    matches = list(set(re.findall(pattern, text)))
    
    if not matches:
        return text
        
    def get_img_url(query):
        return query, fetch_real_image(query)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(get_img_url, matches)
        
    for query, url in results:
        text = text.replace(f"[REAL_IMG: {query}]", url)
        
    return text

# --- THE DAILY AI TREND SCOUT ---
@st.cache_data(ttl=86400, show_spinner=False) # Caches the output for exactly 24 hours
def get_trending_destinations():
    """Fetches trending destinations for HK travelers autonomously and gets real photos."""
    try:
        agent = Agent(
            name="Trend Scout",
            model=Gemini(id="gemini-2.5-flash"), 
            instructions=[
                "You are an expert travel trend analyst for the Hong Kong market.",
                "Identify the top 3 trending international travel destinations for Hong Kong tourists right now. Consider seasonal trends, favorable exchange rates (like the Japanese Yen), and current popularity.",
                "Return ONLY a valid JSON array. Do NOT wrap it in markdown backticks (```json).",
                'Format exactly like this: [{"destination": "City, Country", "description": "Short catchy description (max 10 words)"}]'
            ]
        )
        response = agent.run("Get top 3 trending destinations for HK tourists.", stream=False).content
        
        # Strip potential markdown formatting just in case
        cleaned_response = response.replace("```json", "").replace("```", "").strip()
        destinations = json.loads(cleaned_response)
        
        # Fetch real photos using the waterfall engine
        for dest in destinations[:3]:
            dest['image_url'] = fetch_real_image(dest['destination'])
            
        return destinations[:3]
    except Exception as e:
        # Failsafe: Static trends if AI or internet fails
        return [
            {"destination": "Tokyo, Japan", "description": "Neon lights, ancient temples, and culinary perfection.", "image_url": "[https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=600&h=400&q=80](https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=600&h=400&q=80)"},
            {"destination": "Paris, France", "description": "Art, romance, and café culture by the Seine.", "image_url": "[https://images.unsplash.com/photo-1499856871958-5b9627545d1a?auto=format&fit=crop&w=600&h=400&q=80](https://images.unsplash.com/photo-1499856871958-5b9627545d1a?auto=format&fit=crop&w=600&h=400&q=80)"},
            {"destination": "Banff, Canada", "description": "Crystal lakes, towering peaks, and ultimate wilderness.", "image_url": "[https://images.unsplash.com/photo-1550236520-7050f3582da0?auto=format&fit=crop&w=600&h=400&q=80](https://images.unsplash.com/photo-1550236520-7050f3582da0?auto=format&fit=crop&w=600&h=400&q=80)"}
        ]

# --- SIDEBAR: DASHBOARD LAYOUT ---
with st.sidebar:
    st.image("[https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png](https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png)", width=50)
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
    st.session_state.dest_name = destination
    st.session_state.trip_params = {
        "days": num_days,
        "month": travel_month,
        "budget": budget,
        "persona": traveler_persona
    }

    if not SYSTEM_GOOGLE_KEY:
        st.error("🚨 API Key missing!")
        st.stop()
        
    # Reset displays before generating
    st.session_state.itinerary_data = None
    st.session_state.celebrated = False

# --- MAIN SCREEN AREA ---

# Empty State: Dynamic Inspiration Gallery
if not generate_btn and not st.session_state.itinerary_data:
    st.markdown('<h1 style="text-align: center; font-size: 3.5rem; font-weight: 900; margin-bottom: 0;">🌍 Destination Design Lab</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.3rem; color: #64748b; margin-bottom: 40px;">Design your perfect travel itinerary</p>', unsafe_allow_html=True)
    st.info("👈 Use the Dashboard on the left to configure your parameters and generate a custom AI dossier!")
    
    st.markdown("### 📈 Trending Now for Hong Kong Travelers")
    
    with st.spinner("🤖 AI Scout is fetching today's top travel trends..."):
        trending_places = get_trending_destinations()
        
    cols = st.columns(3)
    for i, col in enumerate(cols):
        if i < len(trending_places):
            place = trending_places[i]
            with col:
                st.image(place.get("image_url", "[https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=600&h=400&q=80](https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=600&h=400&q=80)"), use_container_width=True)
                st.markdown(f"#### 📍 {place.get('destination', 'Unknown')}")
                st.caption(place.get('description', ''))

# Active State: Generating or Displaying Results
if generate_btn or st.session_state.itinerary_data:
    
    disp_dest = st.session_state.dest_name if st.session_state.dest_name else destination
    disp_days = st.session_state.trip_params.get("days", num_days)
    disp_month = st.session_state.trip_params.get("month", travel_month)
    disp_budget = st.session_state.trip_params.get("budget", budget)
    disp_persona = st.session_state.trip_params.get("persona", traveler_persona)

    st.markdown(f'<h1 style="text-align: center; font-size: 3rem; font-weight: 900;">{disp_dest.upper()}</h1>', unsafe_allow_html=True)
    
    safe_dest = urllib.parse.quote(disp_dest)
    st.image(f"[https://image.pollinations.ai/prompt/Beautiful+Cinematic+Landscape+Photography+of](https://image.pollinations.ai/prompt/Beautiful+Cinematic+Landscape+Photography+of)+{safe_dest}?width=1200&height=350", use_container_width=True)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📍 Destination", disp_dest)
    m2.metric("🗓️ Duration", f"{disp_days} Days ({disp_month})")
    m3.metric("💰 Budget", disp_budget)
    m4.metric("👥 Persona", disp_persona)
    st.markdown("---")

    # --- THE ENTERTAINING LOADING SCREEN ---
    if generate_btn:
        status_container = st.empty()
        with status_container.status("🤖 **AI Agents researching in parallel...**", expanded=True) as status:
            loading_msg = st.empty() # Dynamic rotating text container
            
            fallback_models = ["gemini-3-flash-preview", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash"]
            success = False
            raw_content = ""
            last_error = ""
            
            for model_id in fallback_models:
                try:
                    st.write(f"⚙️ Initializing Engine: `{model_id}`...")
                    
                    agent_tools = []
                    if SYSTEM_SERPAPI_KEY:
                        agent_tools = [SerpApiTools(api_key=SYSTEM_SERPAPI_KEY)]
                    
                    def get_itinerary():
                        agent = Agent(
                            name="Itinerary Planner",
                            model=Gemini(id=model_id),
                            tools=agent_tools,
                            instructions=[
                                f"You are the Itinerary Planner for a {disp_days}-day trip to {disp_dest} in {disp_month}.",
                                f"Traveler: '{disp_persona}'. Budget: '{disp_budget}'. Preferences: '{user_preferences}'.",
                                "Generate ONLY the day-by-day schedule.",
                                # OPTION 3 REQUIREMENT: Strict Header formatting
                                "CRITICAL: You MUST start every single day with this exact header format: `## Day [Number]: [Theme of the Day]` (e.g., `## Day 1: Arrival & City Exploration`).",
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
                        return agent.run(f"Create the day-by-day itinerary for {disp_dest}.", stream=False).content

                    def get_logistics():
                        agent = Agent(
                            name="Logistics Expert",
                            model=Gemini(id=model_id),
                            tools=agent_tools,
                            instructions=[
                                f"You are the Logistics Expert for a trip to {disp_dest}.",
                                "Generate ONLY practical logistics and local rules.",
                                "- **Flight & Airports:** Major entry points.",
                                "- **Weather:** What to pack for this month.",
                                "- **Transport:** Best way to get around.",
                                "- **Etiquette:** 3 local rules to respect."
                            ]
                        )
                        return agent.run(f"Gather logistics for {disp_dest}.", stream=False).content

                    def get_hotels(itin_text):
                        agent = Agent(
                            name="Hotel Concierge",
                            model=Gemini(id=model_id),
                            tools=agent_tools,
                            instructions=[
                                f"Find 3 highly-rated hotels in {disp_dest} that fit the {disp_persona} persona.",
                                "For EVERY hotel, use this exact layout:",
                                "### 🏨 [Hotel Name]",
                                "**[🗺️ View on Google Maps](https://www.google.com/maps/search/?api=1&query=Hotel+Name)**",
                                "<br><br>",
                                "<img src=\"[REAL_IMG: Hotel Name, City]\">",
                                "<br><br>",
                                "*Write a short explanation.*"
                            ]
                        )
                        return agent.run(f"Find 3 highly-rated hotels in {disp_dest}.", stream=False).content

                    def get_editor(itin_text):
                        agent = Agent(
                            name="Chief Editor",
                            model=Gemini(id=model_id),
                            instructions=[
                                f"Write a short, engaging, 1-paragraph 'Executive Welcome' for a {disp_persona} traveling to {disp_dest}."
                            ]
                        )
                        return agent.run(f"Write the Executive Welcome.", stream=False).content

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        st.write("🚀 **Phase 1:** Planning Itinerary & Logistics...")
                        future_itin = executor.submit(get_itinerary)
                        future_logistics = executor.submit(get_logistics)
                        
                        # Entertaining Polling Loop 1
                        msgs1 = ["🗺️ Mapping out optimal routes...", "🕵️‍♂️ Asking locals for hidden gems...", "📝 Drafting day-by-day plans..."]
                        i = 0
                        while not (future_itin.done() and future_logistics.done()):
                            loading_msg.info(msgs1[i % len(msgs1)])
                            i += 1
                            time.sleep(1.5)
                        
                        itinerary_content = future_itin.result()
                        logistics_content = future_logistics.result()
                        
                        st.write("🚀 **Phase 2:** Scouting Hotels & Writing Welcome...")
                        future_hotel = executor.submit(get_hotels, itinerary_content)
                        future_editor = executor.submit(get_editor, itinerary_content)
                        
                        # Entertaining Polling Loop 2
                        msgs2 = ["🏨 Checking room availabilities...", "🛎️ Contacting hotel concierges...", "✍️ Polishing the executive summary..."]
                        i = 0
                        while not (future_hotel.done() and future_editor.done()):
                            loading_msg.info(msgs2[i % len(msgs2)])
                            i += 1
                            time.sleep(1.5)
                        
                        hotel_content = future_hotel.result()
                        summary_content = future_editor.result()
                        
                        st.write("📸 **Phase 3:** Executing Waterfall Image Engine...")
                        future_itin_img = executor.submit(process_images, itinerary_content)
                        future_hotel_img = executor.submit(process_images, hotel_content)
                        
                        # Entertaining Polling Loop 3
                        msgs3 = ["📸 Fetching cinematic photos...", "🖼️ Formatting the visual gallery...", "🎨 Applying finishing touches..."]
                        i = 0
                        while not (future_itin_img.done() and future_hotel_img.done()):
                            loading_msg.info(msgs3[i % len(msgs3)])
                            i += 1
                            time.sleep(1.5)
                            
                        itinerary_content = future_itin_img.result()
                        hotel_content = future_hotel_img.result()
                        loading_msg.success("✨ Finalizing your dossier!")

                    # Note the strict separation to ensure parsing works perfectly
                    raw_content = f"{summary_content}\n\n---TAB_SEPARATOR---\n\n{itinerary_content}\n\n---TAB_SEPARATOR---\n\n{hotel_content}\n\n---TAB_SEPARATOR---\n\n{logistics_content}"
                    
                    success = True
                    break 
                    
                except Exception as e:
                    last_error = str(e)
                    st.write(f"⚠️ `{model_id}` error. Switching to next engine...")
                    time.sleep(1)
                    continue
                    
            if success:
                st.session_state.itinerary_data = raw_content
                status_container.empty() # Clear loading status for instant display
                st.rerun() 
            else:
                status.update(label="❌ **Generation Failed**", state="error", expanded=True)
                st.error("🚨 All AI engines have hit limits or failed.")
                st.code(f"Technical Error Data: {last_error}")

    elif st.session_state.itinerary_data:
        if not st.session_state.celebrated:
            st.balloons()
            st.toast('Your custom itinerary has been successfully generated!', icon='🎉')
            st.session_state.celebrated = True
        
        parts = st.session_state.itinerary_data.split("---TAB_SEPARATOR---")
        
        if len(parts) >= 4:
            # Editor's Welcome sits beautifully outside the tabs
            st.markdown(f"### 📝 Editor's Welcome\n{parts[0]}", unsafe_allow_html=True)
            st.markdown("---")
            
            tab1, tab2, tab3 = st.tabs(["🗺️ Day-by-Day Itinerary", "🏨 Accommodations", "🛂 Logistics & Practicalities"])
            
            with tab1:
                # OPTION 3: ACCORDION STYLE ITINERARY PARSING
                itin_text = parts[1]
                # Split the text beautifully by the mandatory Day header
                days = re.split(r'(## Day \d+:.*)', itin_text)
                
                if len(days) > 1:
                    # Render any introductory text before Day 1
                    if days[0].strip():
                        st.markdown(days[0], unsafe_allow_html=True)
                    
                    # Loop through headers and content chunks
                    for i in range(1, len(days), 2):
                        day_header = days[i].replace("## ", "").strip()
                        day_content = days[i+1] if i+1 < len(days) else ""
                        
                        # Expand the very first day by default, collapse the rest
                        with st.expander(day_header, expanded=(i==1)):
                            st.markdown(day_content, unsafe_allow_html=True)
                else:
                    # Fallback just in case AI ignores formatting rules
                    st.markdown(itin_text, unsafe_allow_html=True)
                    
            with tab2:
                st.markdown(f"## 🏨 Top Accommodation Picks\n{parts[2]}", unsafe_allow_html=True)
            with tab3:
                st.markdown(f"## 🛂 Logistics & Practicalities\n{parts[3]}", unsafe_allow_html=True)
        else:
            st.warning("Displaying full dossier below:")
            st.markdown(st.session_state.itinerary_data, unsafe_allow_html=True)
        
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
