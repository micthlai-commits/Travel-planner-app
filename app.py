import streamlit as st
import streamlit.components.v1 as components
import os
import time
from agno.agent import Agent
from agno.tools.serpapi import SerpApiTools
from agno.models.google import Gemini

# --- CONFIGURATION & SECRETS ---
st.set_page_config(page_title="Academic Travel Planner", layout="wide", page_icon="🎓")

# --- CUSTOM CSS FOR UI STYLING & PDF PRINTING ---
st.markdown("""
<style>
    /* Timeline & Visual Styles */
    .stMarkdown img {
        border-radius: 12px;
        max-height: 350px;
        object-fit: cover;
        width: 100%;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }
    .stMarkdown img:hover {
        transform: scale(1.02);
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
    .stMarkdown h2 { color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 30px;}
    .stMarkdown h3 { color: #1f77b4; padding-top: 15px; }
    
    /* 🖨️ PRINT TO PDF STYLES */
    @media print {
        /* Hide all user input elements, buttons, and Streamlit menus when saving to PDF */
        header, footer, .stTextInput, .stNumberInput, .stTextArea, .stSelectbox, .stSlider, .stButton, iframe {
            display: none !important;
        }
        /* Ensure text is black and readable even if the user is in Dark Mode */
        .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown li {
            color: black !important;
        }
        /* Prevent images and transit blocks from breaking across pages */
        img { page-break-inside: avoid; }
        blockquote { page-break-inside: avoid; }
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
    st.error("🚨 API Keys missing! Please check Streamlit Secrets or lines 39/40.")
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

# --- SINGLE MASTER AGENT ARCHITECTURE (LIVE SEARCH ENABLED) ---
if st.button("✈️ Generate Custom Itinerary (Costs 1 Request)", use_container_width=True):
    
    status_container = st.empty()
    status_container.info("🧠 Master AI is searching the live internet and planning your trip... (This takes about 20-30 seconds)")
    
    try:
        master_agent = Agent(
            name="Master Travel Architect",
            role="Expert Travel Planner",
            instructions=[
                f"You are building a complete {num_days}-day travel dossier for {destination} in {travel_month}.",
                f"The traveler is a '{traveler_persona}' on a '{budget}' budget.",
                f"CRITICAL RULES: The user requested these specific preferences: '{user_preferences}'. Your ENTIRE itinerary must revolve around these preferences.",
                "USE YOUR WEB SEARCH TOOL to find up-to-date information on visas, currently open hotels, and real-time logistics.",
                "Generate a single, beautifully formatted Markdown document divided into these sections:",
                "",
                "## 🛂 Part 1: Logistics & Practicalities (Live Data)",
                "- **Flight & Airports:** Major entry points.",
                "- **Weather:** What to pack for this month.",
                "- **Transport:** Best way to get around.",
                "- **Etiquette:** 3 local rules to respect.",
                "",
                "## 🏨 Part 2: Top Accommodation Picks",
                "- Provide 3 currently operating hotel recommendations fitting the budget and preferences.",
                "- For EVERY hotel, you MUST include a photo and map link using this exact layout:",
                "",
                "  ### 🏨 [Hotel Name]",
                "  **[🗺️ View on Google Maps](https://www.google.com/maps/search/?api=1&query=Hotel+Name)**",
                "  <br><br>",
                "  <img src=\"https://image.pollinations.ai/prompt/Hotel+Name+City+Exterior+Photography\">",
                "  <br><br>",
                "  *Write a short explanation of why this fits the user.*",
                "",
                "## 🗓️ Part 3: The Day-by-Day Itinerary",
                "Create the day-by-day schedule. Group locations geographically. Break each day into Morning, Afternoon, and Evening.",
                "For EVERY single location or restaurant, you MUST use this exact layout (with the HTML tags):",
                "",
                "### 📍 [Name of Location]",
                "**⏱️ Suggested Time:** [e.g., 2 hours] | **[🗺️ View on Google Maps](https://www.google.com/maps/search/?api=1&query=Location+Name)**",
                "<br><br>",
                "<img src=\"https://image.pollinations.ai/prompt/Location+Name+City+Tourism+Photography\">",
                "<br><br>",
                "*Write a short, engaging description.*",
                "",
                "> 🚊 **Transit:** [Realistic time, e.g., 15 mins by bus] to next location",
                "",
                "CRITICAL IMAGE RULE: For the `<img src=\"...\">` tags, you MUST replace spaces with a plus sign `+` and REMOVE ALL SPECIAL CHARACTERS (like &, -, '). Use ONLY letters and plus signs! Example: `<img src=\"https://image.pollinations.ai/prompt/Fushimi+Inari+Shrine+Kyoto+Photography\">`."
            ],
            model=Gemini(id="gemini-3-flash-preview"),
            tools=[SerpApiTools(api_key=SERPAPI_KEY)],
        )

        prompt = f"Use your web search tools to generate the comprehensive, up-to-date {num_days}-day travel dossier for {destination}."
        response = master_agent.run(prompt, stream=False)
        
        status_container.success("✅ Master Dossier Complete! (Internet research applied)")
        
        st.markdown(response.content, unsafe_allow_html=True)
        
        # --- DOWNLOAD & PDF EXPORT BUTTONS ---
        st.markdown("---")
        colA, colB = st.columns(2)
        
        with colA:
            st.download_button(
                label="📄 Download Raw Markdown (.md)",
                data=response.content,
                file_name=f"Custom_Itinerary_{destination.replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True
            )
            
        with colB:
            # Injecting a Javascript "Print to PDF" button that triggers the browser's native PDF generator
            components.html(
                """
                <script>
                function printPage() {
                    window.parent.print();
                }
                </script>
                <button onclick="printPage()" style="width: 100%; padding: 0.5rem 1rem; background-color: #ffffff; border: 1px solid rgba(49, 51, 63, 0.2); border-radius: 0.5rem; color: #31333F; font-family: 'Source Sans Pro', sans-serif; font-size: 1rem; cursor: pointer; transition: all 0.2s ease;">
                    🖨️ Save as PDF
                </button>
                <style>
                    button:hover {
                        border-color: #ff4b4b !important;
                        color: #ff4b4b !important;
                    }
                </style>
                """,
                height=50
            )
            
    except Exception as e:
        status_container.error(f"An error occurred: {str(e)}")
        if "429" in str(e) or "quota" in str(e).lower():
            st.error("🚨 You have hit your 20-request limit for the day on this model. The quota will reset at 4:00 PM Hong Kong Time. Alternatively, switch `gemini-3-flash-preview` to `gemini-2.5-flash` in the code to use your other bucket!")
