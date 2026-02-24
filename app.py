import streamlit as st
import os
import time
from agno.agent import Agent
from agno.tools.serpapi import SerpApiTools
from agno.models.google import Gemini

# --- CONFIGURATION & SECRETS ---
st.set_page_config(page_title="Academic Travel Planner", layout="wide", page_icon="🎓")

# --- CUSTOM CSS FOR TIMELINE & UI STYLING ---
st.markdown("""
<style>
    .stMarkdown img {
        border-radius: 12px;
        max-height: 280px;
        object-fit: cover;
        width: 100%;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stMarkdown blockquote {
        border-left: 5px solid #ff4b4b; 
        background-color: rgba(255, 75, 75, 0.05);
        padding: 12px 15px;
        border-radius: 0 8px 8px 0;
        font-size: 0.95em;
        font-weight: 500;
        margin: 20px 0 20px 15px;
    }
    .stMarkdown h3 { padding-top: 15px; color: #1f77b4; }
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
    st.error("🚨 API Keys missing! Please paste your keys into lines 31 and 32 of the code.")
    st.stop()

# --- HEADER ---
st.markdown('<h1 style="text-align: center;">🎓 Destination & Itinerary Design Lab</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; font-size: 1.2rem;">Type your specific travel preferences below, and the AI will build a custom itinerary.</p>', unsafe_allow_html=True)
st.markdown("---")

# --- USER INPUTS ---
st.subheader("1. ✈️ The Basics")
col1, col2 = st.columns(2)

with col1:
    destination = st.text_input("🛬 Destination (City/Region):", "Kyoto, Japan")
with col2:
    num_days = st.number_input("📅 Duration (Days):", min_value=1, max_value=14, value=4)

st.markdown("---")
st.subheader("2. 🎯 Travel Preferences")

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

# --- 4-AGENT ARCHITECTURE (Model-Mixed for Quota Saving) ---
def get_agents():
    # We are removing "instructions=[]" because Gemma 3 models do not 
    # support the "Developer Instruction" (System Prompt) API field yet.
    # Instead, we will feed the instructions directly as the user prompt!
    
    researcher = Agent(
        name="Destination Researcher",
        model=Gemini(id="gemma-3-27b-it"),
        tools=[SerpApiTools(api_key=SERPAPI_KEY)],
    )

    hotel_finder = Agent(
        name="Accommodation Expert",
        model=Gemini(id="gemma-3-12b-it"),
        tools=[SerpApiTools(api_key=SERPAPI_KEY)],
    )

    logistics_agent = Agent(
        name="Logistics Specialist",
        model=Gemini(id="gemma-3-4b-it"),
        tools=[SerpApiTools(api_key=SERPAPI_KEY)],
    )

    planner = Agent(
        name="Itinerary Architect",
        model=Gemini(id="gemma-3-27b-it"),
    )
    return researcher, hotel_finder, logistics_agent, planner

# --- MAIN EXECUTION ---
if st.button("✈️ Generate Custom Itinerary", use_container_width=True):
    
    researcher, hotel_finder, logistics_agent, planner = get_agents()
    
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Final Itinerary", "🏛️ Attractions & Maps", "🏨 Hospitality & Maps", "🛂 Logistics & Weather"])
    
    status_container = st.empty()
    
    try:
        # Step 1: Research
        status_container.info(f"🔍 Agent 1 (Researcher: gemma-3-27b-it) is finding attractions...")
        research_prompt = f"""
ROLE: Tourism Research Specialist

Conduct an in-depth analysis of {destination} for a trip taking place in {travel_month}.
Focus heavily on the constraints of a '{traveler_persona}'.
CRITICAL: The user requested these specific preferences: '{user_preferences}'. You MUST tailor the attractions to match this exact description.

Identify 5 to 8 key attractions that fit the user's description. For EACH attraction, provide:
1. Its significance and why it matches the user's preferences.
2. Estimated time required for a visit.
3. A clickable Google Maps link. Format exactly: `[🗺️ View on Google Maps](https://www.google.com/maps/search/?api=1&query=Location+Name)`. Replace spaces in the query with a plus sign `+`.
4. A photograph. DO NOT use Markdown formatting. You MUST use an HTML image tag. Format exactly: `<img src="https://image.pollinations.ai/prompt/Location+Name+City">`. CRITICAL RULE: Replace spaces with a plus sign `+` and REMOVE ALL SPECIAL CHARACTERS.
"""
        research_response = researcher.run(research_prompt, stream=False)
        with tab2:
            st.markdown(research_response.content, unsafe_allow_html=True)

        status_container.warning("⏳ Cooling down for 8 seconds to avoid Google AI free-tier rate limits...")
        time.sleep(8)

        # Step 2: Hospitality
        status_container.info(f"🏨 Agent 2 (Accommodation: gemma-3-12b-it) is finding {budget} hotels...")
        hotel_prompt = f"""
ROLE: Hospitality & Dining Scout

Find 3 accommodation options in {destination} fitting a '{budget}' budget and suitable for a '{traveler_persona}'.
CRITICAL REQUIREMENT: Ensure the hotels and restaurants strictly follow these user preferences: '{user_preferences}'.
Explain WHY each hotel fits the user's specific request.

Identify 4 highly-rated local restaurants that match their food preferences.
For EVERY hotel and restaurant, provide a Google Maps link exactly: `[🗺️ View on Google Maps](https://www.google.com/maps/search/?api=1&query=Place+Name)`. Replace spaces with a plus sign `+`.
For EVERY hotel and restaurant, DO NOT use Markdown formatting. You MUST use an HTML image tag. Format exactly: `<img src="https://image.pollinations.ai/prompt/Place+Name+City">`. CRITICAL RULE: Replace spaces with a plus sign `+` and REMOVE ALL SPECIAL CHARACTERS.
"""
        hotel_response = hotel_finder.run(hotel_prompt, stream=False)
        with tab3:
            st.markdown(hotel_response.content, unsafe_allow_html=True)
            
        status_container.warning("⏳ Cooling down for 8 seconds to avoid Google AI free-tier rate limits...")
        time.sleep(8)

        # Step 3: Logistics 
        status_container.info(f"🛂 Agent 3 (Logistics: gemma-3-4b-it) is gathering transit & weather info...")
        logistics_prompt = f"""
ROLE: Travel Practicalities Expert

Research practical travel information for tourists traveling to {destination} in {travel_month}.
Provide the following sections clearly formatted in Markdown:
1. **Flight & Entry Logistics**: What are the major airports? What are the general visa requirements?
2. **Local Transportation**: What is the best way to get around {destination}?
3. **Cultural Etiquette & Taboos**: What are 3 crucial behavioral rules tourists should follow here?
4. **Seasonal Weather & Packing ({travel_month})**: What should tourists pack?
"""
        logistics_response = logistics_agent.run(logistics_prompt, stream=False)
        with tab4:
            st.markdown(logistics_response.content, unsafe_allow_html=True)
            
        status_container.warning("⏳ Cooling down for 8 seconds to avoid Google AI free-tier rate limits...")
        time.sleep(8)

        # Step 4: Synthesis
        status_container.info("📝 Agent 4 (Master Planner: gemma-3-27b-it) is building your perfect day-by-day schedule...")
        plan_prompt = f"""
ROLE: Senior Travel Planner

You are teaching students how to build a {num_days}-day itinerary in {destination} for a '{traveler_persona}'.
The user specifically wants this type of trip: '{user_preferences}'. Make sure the pacing matches this!

Use the attractions and hotels provided below to build a day-by-day schedule.
CRITICAL: Focus on geographical routing. Group locations that are close to each other on the same day.
---
FORMATTING RULES FOR A BEAUTIFUL TIMELINE ITINERARY:
1. Start each day with a clear header (e.g., '## 🗓️ Day 1: Exploring Historic Districts').
2. Break down each day into **🌅 Morning**, **☀️ Afternoon**, and **🌙 Evening**.
3. For every single location or restaurant, you MUST use this exact layout:

   ### 📍 [Name of Location]
   **⏱️ Suggested Time:** [e.g., 2 hours] | **[🗺️ View on Google Maps](https://www.google.com/maps/search/?api=1&query=Location+Name)**
   <br><br>
   [INSERT THE EXACT HTML <img src="..."> TAG PROVIDED BY THE PREVIOUS AGENTS HERE]
   <br><br>
   *Write a short, engaging description of what to do here.*

4. BETWEEN each location, you MUST use a Markdown Blockquote to show the transit time. It must look exactly like this:
   > 🚊 **Transit:** [Realistic time, e.g., 15 mins by bus] to next location
5. CRITICAL IMAGE RULE: You MUST copy the actual image URLs provided by the other agents. Do NOT literally write 'url_from_previous_agents'. Make sure every location has a valid `<img src="https://image.pollinations.ai/...">` HTML tag.

---
HERE IS THE RESEARCH TO COMBINE:

**RESEARCHED ATTRACTIONS:**
{research_response.content}

**RESEARCHED HOTELS & RESTAURANTS:**
{hotel_response.content}
"""
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
