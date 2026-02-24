import streamlit as st
import streamlit.components.v1 as components
import os
import urllib.parse
from agno.agent import Agent
from agno.tools.serpapi import SerpApiTools
from agno.models.google import Gemini

# --- CONFIGURATION & SECRETS ---
st.set_page_config(page_title="Academic Travel Planner", layout="wide", page_icon="✈️", initial_sidebar_state="expanded")

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

# --- SIDEBAR: DASHBOARD LAYOUT (Upgrade 1) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png", width=50)
    st.markdown("### ⚙️ Trip Configuration")
    
    destination = st.text_input("🛬 Destination:", "Kyoto, Japan")
    
    col1, col2 = st.columns(2)
    with col1:
        num_days = st.number_input("📅 Days:", min_value=1, max_value=14, value=4)
    with col2:
        travel_month = st.selectbox("🗓️ Month:", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], index=2)
        
    traveler_persona = st.selectbox("👥 Persona:", ["Solo Independent Traveler", "Couple / DINKs", "Family with Young Children", "Seniors / Retirees", "Student Group"])
    budget = st.select_slider("💰 Budget Level:", options=["Budget/Backpacker", "Mid-Range", "Luxury/Boutique"], value="Mid-Range")
    
    user_preferences = st.text_area(
        "✍️ Custom Preferences:",
        placeholder="E.g., I love outdoor hiking but hate crowded museums. Need a pool.",
        height=120
    )
    
    st.markdown("---")
    # Generate button moved to the sidebar!
    generate_btn = st.button("✨ Generate Premium Itinerary", use_container_width=True, type="primary")

# --- MAIN SCREEN AREA ---

# Empty State: Inspiration Gallery (Upgrade 3)
if not generate_btn:
    st.markdown('<h1 style="text-align: center; font-size: 3.5rem; font-weight: 900; margin-bottom: 0;">🌍 Destination Design Lab</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.3rem; color: #64748b; margin-bottom: 40px;">Design your perfect academic travel itinerary</p>', unsafe_allow_html=True)
    
    st.info("👈 Use the Dashboard on the left to configure your parameters and generate a custom AI dossier!")
    
    st.markdown("### ✨ Inspiration Gallery")
    gal1, gal2, gal3 = st.columns(3)
    
    with gal1:
        # Added &h=400 to force a 3:2 aspect ratio crop for uniformity
        st.image("https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=600&h=400&q=80", use_container_width=True)
        st.markdown("#### 🗼 Tokyo, Japan")
        st.caption("Neon lights, ancient temples, and culinary perfection.")
    with gal2:
        # Added &h=400 to force a 3:2 aspect ratio crop for uniformity
        st.image("https://images.unsplash.com/photo-1499856871958-5b9627545d1a?auto=format&fit=crop&w=600&h=400&q=80", use_container_width=True)
        st.markdown("#### 🥐 Paris, France")
        st.caption("Art, romance, and café culture by the Seine.")
    with gal3:
        # Added &h=400 to force a 3:2 aspect ratio crop for uniformity
        st.image("https://images.unsplash.com/photo-1550236520-7050f3582da0?auto=format&fit=crop&w=600&h=400&q=80", use_container_width=True)
        st.markdown("#### 🏔️ Banff, Canada")
        st.caption("Crystal lakes, towering peaks, and ultimate wilderness.")

# Active State: Itinerary Generation
if generate_btn:
    st.markdown(f'<h1 style="text-align: center; font-size: 3rem; font-weight: 900;">{destination.upper()}</h1>', unsafe_allow_html=True)
    
    # Hero Banner
    safe_dest = urllib.parse.quote(destination)
    st.image(f"https://image.pollinations.ai/prompt/Beautiful+Cinematic+Landscape+Photography+of+{safe_dest}?width=1200&height=350", use_container_width=True)
    
    # Trip Summary Metric Cards (Upgrade 2)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📍 Destination", destination)
    m2.metric("🗓️ Duration", f"{num_days} Days ({travel_month})")
    m3.metric("💰 Budget", budget)
    m4.metric("👥 Persona", traveler_persona)
    
    st.markdown("---")
    
    with st.status("🤖 **Master AI is researching and routing your dossier...**", expanded=True) as status:
        st.write("🔍 Searching the live internet for up-to-date logistics...")
        st.write("🏨 Scouting accommodations that match your budget...")
        st.write("🗺️ Organizing tabs and formatting photography...")
        
        try:
            master_agent = Agent(
                name="Master Travel Architect",
                role="Expert Travel Planner",
                instructions=[
                    f"You are building a complete {num_days}-day travel dossier for {destination} in {travel_month}.",
                    f"The traveler is a '{traveler_persona}' on a '{budget}' budget.",
                    f"CRITICAL RULES: The user requested these specific preferences: '{user_preferences}'. Your ENTIRE itinerary must revolve around these preferences.",
                    "USE YOUR WEB SEARCH TOOL to find up-to-date information on visas, currently open hotels, and real-time logistics.",
                    "---",
                    "CRITICAL FORMATTING RULE FOR TABS:",
                    "You MUST divide your document into 3 distinct sections using EXACTLY this text separator on its own line: `---TAB_SEPARATOR---`",
                    "If you do not use `---TAB_SEPARATOR---` exactly twice, the app will break.",
                    "---",
                    "## 🛂 Part 1: Logistics & Practicalities",
                    "- **Flight & Airports:** Major entry points.",
                    "- **Weather:** What to pack for this month.",
                    "- **Transport:** Best way to get around.",
                    "- **Etiquette:** 3 local rules to respect.",
                    "",
                    "---TAB_SEPARATOR---",
                    "",
                    "## 🏨 Part 2: Top Accommodation Picks",
                    "- Provide 3 currently operating hotel recommendations fitting the budget and preferences.",
                    "- For EVERY hotel, you MUST include a photo and map link using this exact layout:",
                    "  ### 🏨 [Hotel Name]",
                    "  **[🗺️ View on Google Maps](https://www.google.com/maps/search/?api=1&query=Hotel+Name)**",
                    "  <br><br>",
                    "  <img src=\"https://image.pollinations.ai/prompt/Hotel+Name+City+Exterior+Photography\">",
                    "  <br><br>",
                    "  *Write a short explanation of why this fits the user.*",
                    "",
                    "---TAB_SEPARATOR---",
                    "",
                    "## 🗓️ Part 3: The Day-by-Day Itinerary",
                    "Create a detailed day-by-day schedule. Include top tourist attractions, historical sites, natural attractions, and hidden gems. Group them geographically.",
                    "Break each day into Morning, Afternoon, and Evening.",
                    "For EVERY single location or restaurant, you MUST use this exact layout:",
                    "### 📍 [Name of Location]",
                    "**⏱️ Suggested Time:** [e.g., 2 hours] | **[🗺️ View on Google Maps](https://www.google.com/maps/search/?api=1&query=Location+Name)**",
                    "<br><br>",
                    "<img src=\"https://image.pollinations.ai/prompt/Location+Name+City+Tourism+Photography\">",
                    "<br><br>",
                    "*Write a short, engaging description.*",
                    "",
                    "> 🚊 **Transit:** [Realistic time, e.g., 15 mins by bus] to next location",
                    "",
                    "CRITICAL IMAGE RULE: For all `<img src=\"...\">` tags, replace spaces with a plus sign `+` and REMOVE ALL SPECIAL CHARACTERS. Use ONLY letters and plus signs!"
                ],
                model=Gemini(id="gemini-3-flash-preview"),
                tools=[SerpApiTools(api_key=SERPAPI_KEY)],
            )

            prompt = f"Use your web search tools to generate the comprehensive, up-to-date {num_days}-day travel dossier for {destination}."
            response = master_agent.run(prompt, stream=False)
            
            status.update(label="✅ **Master Dossier Complete!**", state="complete", expanded=False)
            
            # Celebratory Animations (Upgrade 4)
            st.balloons()
            st.toast('Your custom itinerary has been successfully generated!', icon='🎉')
            
            # Tabbed Navigation (Upgrade 5)
            raw_content = response.content
            parts = raw_content.split("---TAB_SEPARATOR---")
            
            if len(parts) >= 3:
                tab1, tab2, tab3 = st.tabs(["🛂 Logistics & Practicalities", "🏨 Accommodations", "🗺️ Day-by-Day Itinerary"])
                with tab1:
                    st.markdown(parts[0], unsafe_allow_html=True)
                with tab2:
                    st.markdown(parts[1], unsafe_allow_html=True)
                with tab3:
                    st.markdown(parts[2], unsafe_allow_html=True)
            else:
                st.warning("Could not automatically separate the tabs. Displaying full dossier below:")
                st.markdown(raw_content, unsafe_allow_html=True)
            
            # --- DOWNLOAD & PDF EXPORT BUTTONS ---
            st.markdown("---")
            colA, colB = st.columns(2)
            
            with colA:
                st.download_button(
                    label="📄 Download Raw Markdown (.md)",
                    data=raw_content.replace("---TAB_SEPARATOR---", "\n\n---\n\n"),
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
