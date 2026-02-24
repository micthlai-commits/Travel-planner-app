import streamlit as st
import os
import time
from agno.agent import Agent
from agno.tools.serpapi import SerpApiTools
from agno.models.google import Gemini

# --- CONFIGURATION & SECRETS ---
st.set_page_config(page_title="Academic Travel Planner", layout="wide", page_icon="🎓")

# --- CUSTOM CSS FOR TIMELINE & UI STYLING ---
# This makes the markdown look more like a modern travel app (like Funliday)
st.markdown("""
<style>
    /* Style images to look like clean, rounded UI cards */
    .stMarkdown img {
        border-radius: 12px;
        max-height: 280px;
        object-fit: cover;
        width: 100%;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Style blockquotes to look like transit/timeline connectors between places */
    .stMarkdown blockquote {
        border-left: 5px solid #ff4b4b; /* Streamlit's brand red/pink */
        background-color: rgba(255, 75, 75, 0.05);
        padding: 12px 15px;
        border-radius: 0 8px 8px 0;
        font-size: 0.95em;
        font-weight: 500;
        margin: 20px 0 20px 15px;
    }
    
    /* Make h3 location headers pop */
    .stMarkdown h3 {
        padding-top: 15px;
        color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# 👇 PASTE YOUR KEYS INSIDE THE QUOTATION MARKS BELOW 👇
LOCAL_SERPAPI_KEY = "" 
LOCAL_GOOGLE_KEY = "" 
# 👆 ------------------------------------------------ 👆

# Safely load keys depending on whether it's running locally or on Streamlit Cloud
try:
    SERPAPI_KEY = st.secrets["SERPAPI_KEY"] 
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"] 
except Exception:
    SERPAPI_KEY = LOCAL_SERPAPI_KEY
    GOOGLE_API_KEY = LOCAL_GOOGLE_KEY

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

if not GOOGLE_API_KEY or not SERPAPI_KEY:
    st.error("🚨 API Keys missing! Please paste your keys into lines 32 and 33 of the code.")
    st.stop()

# --- HEADER ---
st.markdown('<h1 style="text-align: center;">🎓 Destination & Itinerary Design Lab</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; font-size: 1.2rem;">Type your specific travel preferences below, and the AI will build a custom itinerary.</p>', unsafe_allow_html=True)
st.markdown("---")

# --- USER INPUTS (Inspired by Google Flights) ---
st.subheader("1. ✈️ The Basics")
col1, col2 = st.columns(2)

with col1:
    destination = st.text_input("🛬 Destination (City/Region):", "Kyoto, Japan")
with col2:
    num_days = st.number_input("📅 Duration (Days):", min_value=1, max_value=14, value=4)

st.markdown("---")
st.subheader("2. 🎯 Travel Preferences")

# The open-ended free text box for custom preferences!
user_preferences = st.text_area(
    "✍️ Describe your ideal trip (Type anything you want!):",
    placeholder="E.g., I love outdoor hiking but hate crowded museums. I need a hotel with a swimming pool, and I want to eat a lot of local street food. Keep it relaxing.",
    height=100
)

col4, col5, col6 = st.columns(3)
with col4:
    travel_month = st.selectbox("🗓️ Month of Travel:", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], index=2)
with col5:
    traveler_persona = st.selectbox("👥 Who is traveling?", ["Solo Independent Traveler", "Couple / DINKs", "Family with Young Children", "Seniors / Retirees", "Student Group"])
with col6:
    budget = st.select_slider("💰 Budget Level:", options=["Budget/Backpacker", "Mid-Range", "Luxury/Boutique"], value="Mid-Range")

st.markdown("---")

# --- AI AGENT SETUP ---
def get_agents():
    # Agent 1: The Destination Researcher
    researcher = Agent(
        name="Destination Researcher",
        role="Tourism Research Specialist",
        instructions=[
            f"Conduct an in-depth analysis of {destination} for a trip taking place in {travel_month}.",
            f"Focus heavily on the constraints of a '{traveler_persona}'.",
            f"CRITICAL: The user requested these specific preferences: '{user_preferences}'. You MUST tailor the attractions to match this exact description.",
            "Identify 5 to 8 key attractions that fit the user's description. For EACH attraction, provide:",
            "1. Its significance and why it matches the user's preferences.",
            "2. Estimated time required for a visit.",
            "3. A clickable Google Maps link. Format exactly: `[🗺️ View on Google Maps](https://www.google.com/maps/search/?api=1&query=Location+Name)`. Replace spaces in the query with a plus sign `+`.",
            "4. A photograph. DO NOT use Markdown formatting. You MUST use an HTML image tag. Format exactly: `<img src=\"https://image.pollinations.ai/prompt/Location+Name+City\">`. CRITICAL RULE: You MUST replace spaces with a plus sign `+` and REMOVE ALL SPECIAL CHARACTERS (like &, -, ', etc.) from the URL. Use ONLY letters and plus signs. Example: `<img src=\"https://image.pollinations.ai/prompt/Fushimi+Inari+Shrine+Kyoto\">`"
        ],
        model=Gemini(id="gemini-2.5-flash-lite"),
        tools=[SerpApiTools(api_key=SERPAPI_KEY)],
    )

    # Agent 2: The Accommodation & F&B Specialist
    hotel_finder = Agent(
        name="Accommodation Expert",
        role="Hospitality & Dining Scout",
        instructions=[
            f"Find 3 accommodation options in {destination} fitting a '{budget}' budget and suitable for a '{traveler_persona}'.",
            f"CRITICAL REQUIREMENT: Ensure the hotels and restaurants strictly follow these user preferences: '{user_preferences}'.",
            "Explain WHY each hotel fits the user's specific request.",
            "Identify 4 highly-rated local restaurants that match their food preferences.",
            "For EVERY hotel and restaurant, provide a Google Maps link exactly: `[🗺️ View on Google Maps](https://www.google.com/maps/search/?api=1&query=Place+Name)`. Replace spaces with a plus sign `+`.",
            "For EVERY hotel and restaurant, DO NOT use Markdown formatting. You MUST use an HTML image tag. Format exactly: `<img src=\"https://image.pollinations.ai/prompt/Place+Name+City\">`. CRITICAL RULE: You MUST replace spaces with a plus sign `+` and REMOVE ALL SPECIAL CHARACTERS. Example: `<img src=\"https://image.pollinations.ai/prompt/Ritz+Carlton+Kyoto\">`"
        ],
        model=Gemini(id="gemini-2.5-flash-lite"),
        tools=[SerpApiTools(api_key=SERPAPI_KEY)],
    )

    # Agent 3: The Logistics & Etiquette Specialist
    logistics_agent = Agent(
        name="Logistics Specialist",
        role="Travel Practicalities Expert",
        instructions=[
            f"Research practical travel information for tourists traveling to {destination} in {travel_month}.",
            "Provide the following sections clearly formatted in Markdown:",
            "1. **Flight & Entry Logistics**: What are the major airports? What are the general visa requirements for major tourist demographics?",
            f"2. **Local Transportation**: What is the best way to get around {destination}?",
            "3. **Cultural Etiquette & Taboos**: What are 3 crucial behavioral rules tourists should follow here?",
            f"4. **Seasonal Weather & Packing ({travel_month})**: What should tourists pack?"
        ],
        model=Gemini(id="gemini-2.5-flash-lite"),
        tools=[SerpApiTools(api_key=SERPAPI_KEY)],
    )

    # Agent 4: The Itinerary Architect (Master Agent)
    planner = Agent(
        name="Itinerary Architect",
        role="Senior Travel Planner",
        instructions=[
            f"You are teaching students how to build a {num_days}-day itinerary in {destination} for a '{traveler_persona}'.",
            f"The user specifically wants this type of trip: '{user_preferences}'. Make sure the pacing matches this!",
            "Use the attractions and hotels provided by the other agents to build a day-by-day schedule.",
            "CRITICAL: Focus on geographical routing. Group locations that are close to each other on the same day.",
            "---",
            "FORMATTING RULES FOR A BEAUTIFUL TIMELINE ITINERARY:",
            "1. Start each day with a clear header (e.g., '## 🗓️ Day 1: Exploring Historic Districts').",
            "2. Break down each day into **🌅 Morning**, **☀️ Afternoon**, and **🌙 Evening**.",
            "3. For every single location or restaurant, you MUST use this exact layout:",
            "",
            "   ### 📍 [Name of Location]",
            "   **⏱️ Suggested Time:** [e.g., 2 hours] | **[🗺️ View on Google Maps](https://www.google.com/maps/search/?api=1&query=Location+Name)**",
            "   <br><br>",
            "   <img src=\"url_from_previous_agents\">",
            "   <br><br>",
            "   *Write a short, engaging description of what to do here.*",
            "",
            "4. BETWEEN each location, you MUST use a Markdown Blockquote to show the transit time. It must look exactly like this:",
            "   > 🚊 **Transit:** [Realistic time, e.g., 15 mins by bus] to next location",
            "5. CRITICAL: NEVER use Markdown `![Image](url)`. You MUST use the HTML `<img src=\"...\">` tag exactly as provided by the previous agents, and you MUST include the `<br><br>` tags around it to force proper line spacing."
        ],
        model=Gemini(id="gemini-2.5-flash-lite"),
    )
    return researcher, hotel_finder, logistics_agent, planner

# --- MAIN EXECUTION ---
if st.button("✈️ Generate Custom Itinerary", use_container_width=True):
    
    researcher, hotel_finder, logistics_agent, planner = get_agents()
    
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Final Itinerary", "🏛️ Attractions & Maps", "🏨 Hospitality & Maps", "🛂 Logistics & Weather"])
    
    status_container = st.empty()
    
    try:
        # Step 1: Research
        status_container.info(f"🔍 Agent 1 (Researcher) is finding attractions that match your specific preferences...")
        research_prompt = f"Find attractions in {destination} for a {num_days}-day trip matching these preferences: {user_preferences}."
        research_response = researcher.run(research_prompt, stream=False)
        with tab2:
            st.markdown(research_response.content, unsafe_allow_html=True)

        # PAUSE to respect Google's Free Tier Rate Limits
        status_container.warning("⏳ Cooling down for 8 seconds to avoid Google AI free-tier rate limits...")
        time.sleep(8)

        # Step 2: Hospitality
        status_container.info(f"🏨 Agent 2 (Accommodation Expert) is finding {budget} hotels matching your needs...")
        hotel_prompt = f"Find accommodations and dining in {destination} suitable for {budget} matching: {user_preferences}."
        hotel_response = hotel_finder.run(hotel_prompt, stream=False)
        with tab3:
            st.markdown(hotel_response.content, unsafe_allow_html=True)
            
        # PAUSE to respect Google's Free Tier Rate Limits
        status_container.warning("⏳ Cooling down for 8 seconds to avoid Google AI free-tier rate limits...")
        time.sleep(8)

        # Step 3: Logistics 
        status_container.info(f"🛂 Agent 3 (Logistics Expert) is gathering transit, weather, and entry logistics for {destination}...")
        logistics_prompt = f"Find major airports, general visa rules, and weather for {travel_month} in {destination}."
        logistics_response = logistics_agent.run(logistics_prompt, stream=False)
        with tab4:
            st.markdown(logistics_response.content, unsafe_allow_html=True)
            
        # PAUSE to respect Google's Free Tier Rate Limits
        status_container.warning("⏳ Cooling down for 8 seconds to avoid Google AI free-tier rate limits...")
        time.sleep(8)

        # Step 4: Synthesis
        status_container.info("📝 Agent 4 (Itinerary Architect) is building your perfect day-by-day schedule...")
        plan_prompt = (
            f"Create a {num_days}-day itinerary for {destination}. "
            f"Combine this research: {research_response.content} and these hotels/restaurants: {hotel_response.content}. "
            f"Ensure the pacing strictly aligns with the user's preference: {user_preferences}."
        )
        itinerary_response = planner.run(plan_prompt, stream=False)
        with tab1:
            st.markdown(itinerary_response.content, unsafe_allow_html=True)
            
        status_container.success("✅ Custom Analysis Complete! Review your personalized itinerary below.")
        
        # --- DOWNLOAD BUTTON FOR ASSIGNMENTS ---
        st.markdown("---")
        full_report = f"""# 🎓 Academic Destination Analysis: {destination}
**Persona:** {traveler_persona} | **Month:** {travel_month} | **Budget:** {budget}
**User Custom Preferences:** {user_preferences}

## 1. Destination Attractions
{research_response.content}

## 2. Hospitality & Dining Analysis
{hotel_response.content}

## 3. Logistics & Weather
{logistics_response.content}

## 4. Final Itinerary
{itinerary_response.content}
"""
        st.download_button(
            label="📄 Download Full Report (.md)",
            data=full_report,
            file_name=f"Custom_Itinerary_{destination.replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True
        )
        
    except Exception as e:
        status_container.error(f"An error occurred: {str(e)}")
