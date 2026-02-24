import streamlit as st
import streamlit.components.v1 as components
import os
import time
import urllib.parse
from agno.agent import Agent
from agno.tools.serpapi import SerpApiTools
from agno.models.google import Gemini

# --- CONFIGURATION & SECRETS ---
st.set_page_config(page_title="Academic Travel Planner", layout="wide", page_icon="✈️")

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
        margin-top: 40px;
        font-weight: 800;
    }
    .stMarkdown h3 { 
        color: #2563EB; 
        padding-top: 20px; 
        font-weight: 700;
    }
    
    /* 🖨️ PRINT TO PDF STYLES */
    @media print {
        header, footer, .stTextInput, .stNumberInput, .stTextArea, .stSelectbox, .stSlider, .stButton, iframe, .stExpander {
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

# 👇 PASTE YOUR KEYS INSIDE THE QUOTATION MARKS BELOW 👇
LOCAL_SERPAPI_KEY = "" 
LOCAL_GOOGLE_KEY = "" 
# 👆 ------------------------------------------------ 👆

try:
    SERPAPI_KEY = st.secrets["SERPAPI_KEY"] 
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"] 
except Exception:
    SERPAPI_KEY = LOCAL_SERPAPI_KEY
    GOOGLE_API_KEY = LOCAL_GOOGLE_KEY

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

if not GOOGLE_API_KEY or not SERPAPI_KEY:
    st.error("🚨 API Keys missing! Please check Streamlit Secrets.")
    st.stop()

# --- HERO BANNER AREA ---
st.markdown('<h1 style="text-align: center; font-size: 3rem; font-weight: 900; margin-bottom: 0;">🌍 Destination Design Lab</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #64748b; margin-bottom: 30px;">Design your perfect travel itinerary</p>', unsafe_allow_html=True)

# --- USER INPUTS (Inside a sleek expander) ---
with st.expander("⚙️ **Configure Travel Parameters**", expanded=True):
    st.subheader("1. The Basics")
    col1, col2 = st.columns(2)
    with col1:
        destination = st.text_input("🛬 Destination (City/Region):", "Kyoto, Japan")
    with col2:
        num_days = st.number_input("📅 Duration (Days):", min_value=1, max_value=14, value=4)

    st.markdown("---")
    st.subheader("2. Travel Preferences")
    user_preferences = st.text_area(
        "✍️ Describe your ideal trip:",
        placeholder="E.g., I love outdoor hiking but hate crowded museums. I need a hotel with a swimming pool, and I want to eat a lot of local street food. Keep it relaxing.",
        height=100
    )

    col4, col5, col6 = st.columns(3)
    with col4:
        travel_month = st.selectbox("🗓️ Month:", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], index=2)
    with col5:
        traveler_persona = st.selectbox("👥 Traveler Type:", ["Solo Independent Traveler", "Couple / DINKs", "Family with Young Children", "Seniors / Retirees", "Student Group"])
    with col6:
        budget = st.select_slider("💰 Budget Level:", options=["Budget/Backpacker", "Mid-Range", "Luxury/Boutique"], value="Mid-Range")

# --- MAIN EXECUTION ---
if st.button("✨ Generate Premium Itinerary", use_container_width=True, type="primary"):
    
    # Show a dynamic hero image based on their destination while loading!
    safe_dest = urllib.parse.quote(destination)
    st.image(f"https://image.pollinations.ai/prompt/Beautiful+Cinematic+Landscape+Photography+of+{safe_dest}?width=1200&height=350", use_container_width=True)
    
    # Animated Loading Status
    with st.status("🤖 **Master AI is constructing your dossier...**", expanded=True) as status:
        st.write("🔍 Searching the live internet for up-to-date logistics...")
        st.write("🏨 Scouting accommodations that match your budget...")
        st.write("🗺️ Routing attractions geographically...")
        
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
                    "Create a detailed day-by-day schedule. You MUST include top tourist attractions, historical sites, natural attractions, hidden gems, events, and local activities that match the user's preferences. Group these attractions geographically.",
                    "Break each day into Morning, Afternoon, and Evening.",
                    "For EVERY single attraction, location, or restaurant, you MUST use this exact layout (with the HTML tags):",
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
            
            status.update(label="✅ **Master Dossier Complete!**", state="complete", expanded=False)
            
            # Display final result
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
                
        except Exception as e:
            status.update(label="❌ Error occurred", state="error")
            if "429" in str(e) or "quota" in str(e).lower():
                st.error("🚨 You have hit your 20-request limit for the day on this model. The quota will reset at 4:00 PM Hong Kong Time. Alternatively, switch `gemini-3-flash-preview` to `gemini-2.5-flash` in the code to use your other bucket!")
            else:
                st.error(f"An error occurred: {str(e)}")
