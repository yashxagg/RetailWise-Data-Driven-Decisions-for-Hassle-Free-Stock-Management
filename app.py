
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import init_dynamic_db, insert_dynamic_data, extract_structured_data, create_connection
from processor import extract_text_from_pdf
from ai_features import handle_natural_query, get_restock_suggestions, analyze_expiry_and_pricing, listen_to_voice, generate_dynamic_pricing, analyze_shelf_image
import json
import os
import time

# --- Setup ---
st.set_page_config(
    page_title="RetailWise | Human-Centric AI",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Human-Centric Creative CSS ---
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,700;0,900;1,700&display=swap" rel="stylesheet">
    <style>
        /* Modern Warm Backdrop */
        .stApp {
            background-color: #FDF9F3;
        }

        /* 
           LEAK FIX: Isolated text styling. 
           We only style text within our main content wrapper and cards.
           This prevents "keyboard_double_" leaks by NOT touching Streamlit's internal spans.
        */
        .main-content-wrapper p, 
        .main-content-wrapper span, 
        .main-content-wrapper div, 
        .main-content-wrapper label {
            color: #1A1A1A;
            font-family: 'Outfit', sans-serif;
        }

        /* Organic Typography */
        h1 {
            font-family: 'Playfair Display', serif !important;
            color: #1A1A1A !important;
            font-weight: 900 !important;
            font-size: 3.5rem !important;
            letter-spacing: -0.02em;
            margin-bottom: 0.5rem !important;
        }
        
        h2, h3 {
            font-family: 'Outfit', sans-serif !important;
            color: #1A1A1A !important;
            font-weight: 600 !important;
        }

        /* Clean Sidebar */
        /* Clean Sidebar */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #F0E6D6;
            box-shadow: 5px 0 30px rgba(0,0,0,0.02);
        }
        
        /* Direct Branding Style */
        .sidebar-brand {
            font-family: 'Playfair Display', serif;
            font-size: 2.2rem;
            color: #E67E22 !important;
            text-align: center;
            padding: 40px 0;
            font-weight: 900;
            display: block;
        }
        
        /* Refined Atelier Navigation - Visibility Restore */
        [data-testid="stSidebar"] [data-testid="stRadio"] {
            padding-top: 20px !important;
        }

        /* High-Contrast Baseline for all labels */
        [data-testid="stSidebar"] [data-testid="stRadio"] label p {
            color: #2D3436 !important;
            font-family: 'Outfit', sans-serif !important;
            transition: all 0.3s ease;
        }

        /* Target all radio labels for subtle layout */
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            padding: 10px 15px !important;
            border-radius: 8px !important;
            cursor: pointer !important;
            margin-bottom: 4px !important;
        }

        /* Sophisticated Hover State */
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            background: rgba(44, 62, 80, 0.03) !important;
            transform: translateX(3px);
        }

        /* Premium Active State: "The Atelier Selection" */
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-selected="true"] {
            background: rgba(212, 175, 55, 0.06) !important;
            border-left: 3px solid var(--gold) !important;
            padding-left: 12px !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.02) !important;
        }

        /* Active Text Contrast - Deep Forest */
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-selected="true"] p {
            color: var(--forest) !important;
            font-weight: 700 !important;
            letter-spacing: 0.01em;
        }

        /* Keep the radio indicator but make it more discreet */
        [data-testid="stSidebar"] [data-testid="stRadio"] div[data-testid="stWidgetSelectionResult"] {
            transform: scale(0.85);
            opacity: 0.7;
        }
        
        /* Luxury Atelier Palette */
        :root {
            --forest: #2C3E50;
            --gold: #D4AF37;
            --linen: #FDFBF7;
            --clay: #7D8E7E;
            --ink: #1A1C1E;
        }

        .stApp {
            background-color: var(--linen);
        }

        /* Atelier Gallery Canvas - Refined Spacing */
        .creative-card {
            background: #FFFFFF;
            background-image: 
                linear-gradient(45deg, rgba(212, 175, 55, 0.005) 25%, transparent 25%), 
                linear-gradient(-45deg, rgba(212, 175, 55, 0.005) 25%, transparent 25%);
            background-size: 60px 60px;
            border-radius: 12px; /* Sharper, more sophisticated gallery feel */
            padding: 45px 35px; /* Reduced side padding to prevent wrapping */
            box-shadow: 
                0 40px 100px -30px rgba(44, 62, 80, 0.08),
                0 0 1px rgba(44, 62, 80, 0.1);
            border: 1px solid rgba(44, 62, 80, 0.06);
            margin-bottom: 40px;
            transition: all 0.8s cubic-bezier(0.19, 1, 0.22, 1);
            position: relative;
        }
        
        /* Subtle Atelier Corner Decal */
        .creative-card::before {
            content: '';
            position: absolute;
            top: 15px;
            left: 15px;
            width: 10px;
            height: 10px;
            border-top: 1px solid var(--gold);
            border-left: 1px solid var(--gold);
            opacity: 0.3;
        }

        .creative-card:hover {
            transform: translateY(-6px);
            box-shadow: 0 50px 120px -30px rgba(212, 175, 55, 0.15);
            border-color: rgba(212, 175, 55, 0.3);
        }

        /* Atelier Pedestal Metric - Refined alignment */
        .metric-card {
            text-align: left;
            border-left: 2px solid rgba(212, 175, 55, 0.1);
            padding-left: 25px;
            min-height: 180px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        
        .metric-icon-wrapper {
            font-size: 1.5rem;
            margin-bottom: 15px;
            color: var(--gold);
            opacity: 0.9;
            font-weight: 300;
        }

        .metric-value {
            font-size: clamp(1.8rem, 3.5vw, 3rem); /* Tuned to prevent wrapping */
            font-weight: 300;
            color: var(--forest) !important;
            font-family: 'Playfair Display', serif !important;
            letter-spacing: -0.01em;
            line-height: 1.1;
            margin: 0;
            white-space: nowrap; /* Strong rule to keep it on one line */
        }
        
        .metric-label {
            color: var(--clay) !important;
            text-transform: uppercase;
            letter-spacing: 0.35em;
            font-size: 0.65rem;
            font-weight: 600;
            margin-top: 20px;
            opacity: 0.7;
        }

        /* Atelier Interactive Buttons */
        .stButton > button {
            background: var(--forest) !important;
            color: #FFFFFF !important;
            border-radius: 4px; /* Sophisticated sharp look */
            padding: 16px 32px;
            font-weight: 600;
            border: 1px solid var(--forest);
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.2em;
            font-size: 0.75rem;
        }
        
        .stButton > button:hover {
            background: #1B2121 !important;
            border-color: var(--gold);
            color: var(--gold) !important;
        }

        /* Global Text Visibility Fix - Carefully excluding buttons and specific widgets */
        [data-testid="stMain"] *:not(button):not(button *):not([data-testid="stFileUploader"] *) {
            color: #1A1A1A;
        }
        
        /* High-Contrast Widget Overrides */
        [data-testid="stFileUploader"] {
            background-color: #FFFFFF !important;
            border: 1px dashed rgba(44, 62, 80, 0.2) !important;
            border-radius: 8px !important;
            padding: 20px !important;
        }
        
        [data-testid="stFileUploader"] * {
            color: var(--forest) !important;
        }
        
        /* Input & Form Control Sanitization */
        div[data-testid="stNumberInput"], div[data-testid="stTextInput"], div[data-testid="stTextArea"] {
            background-color: transparent !important;
        }
        
        div[data-testid="stNumberInput"] > div, div[data-testid="stTextInput"] > div, div[data-testid="stTextArea"] > div {
            background-color: #FFFFFF !important;
            border: 1px solid rgba(44, 62, 80, 0.2) !important;
            border-radius: 4px !important;
        }

        /* Target internal input elements specifically */
        input, textarea {
            color: #1A1A1A !important;
            background-color: #FFFFFF !important;
        }

        /* Number Input Buttons (+/-) */
        div[data-testid="stNumberInput"] button {
            background-color: #FDFBF7 !important;
            color: var(--forest) !important;
            border: none !important;
            border-left: 1px solid rgba(44, 62, 80, 0.1) !important;
        }
        
        /* Browse Files Button Fix */
        [data-testid="stFileUploader"] button {
            background: var(--gold) !important;
            color: #FFFFFF !important;
            border: none !important;
        }
        
        /* Force white text specifically for all button content (Primary Buttons) */
        .stButton > button div, .stButton > button p, .stButton > button span {
            color: #FFFFFF !important;
        }

        /* Style Selectboxes */
        div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            border-radius: 4px !important;
            border: 1px solid rgba(44, 62, 80, 0.1) !important;
        }
        
        div[data-baseweb="select"] span {
            color: var(--forest) !important;
        }

        /* CM Chat bubbles - Luxury Correspondence */
        .stChatMessage {
            background: #FFFFFF !important;
            border: 1px solid rgba(44, 62, 80, 0.08) !important;
            border-radius: 8px !important;
            padding: 25px !important;
            box-shadow: 0 10px 40px rgba(0,0,0,0.03) !important;
            margin-bottom: 20px !important;
        }
        
        /* Camera Input & File Uploader Polish */
        [data-testid="stCameraInput"], [data-testid="stFileUploader"] {
            background-color: #FFFFFF !important;
            border: 1px solid rgba(44, 62, 80, 0.1) !important;
            padding: 20px !important;
            border-radius: 8px !important;
        }
        
        /* Assistant message styling */
        [data-testid="stChatMessageAssistant"] {
            border-left: 3px solid var(--gold) !important;
            background: rgba(212, 175, 55, 0.02) !important;
        }
        
        /* User message styling */
        [data-testid="stChatMessageUser"] {
            border-right: 3px solid var(--forest) !important;
        }

        /* Atelier Studio Input */
        .stChatInputContainer {
            border: 1px solid rgba(44, 62, 80, 0.1) !important;
            border-radius: 4px !important;
            background: #FFFFFF !important;
        }

        /* Warm Status Badges */
        .badge {
            padding: 6px 14px;
            border-radius: 100px;
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
        }
        .badge-warm { background: #FEF5E7; color: #E67E22 !important; }
        .badge-cool { background: #E8F8F5; color: #1ABC9C !important; }

        /* Animation */
        @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .stApp { animation: slideUp 0.6s ease-out; }

        /* Hide Streamlit Clutter */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- Wrapping main content to apply styles safely ---
st.markdown('<div class="main-content-wrapper">', unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown('<div class="sidebar-brand">RetailWise</div>', unsafe_allow_html=True)
    
    # Original Functionality Names
    menu_options = {
        "📊 Shop Overview": "Shop Overview",
        "💬 AI Assistant": "AI Assistant",
        "📦 Stock Management": "Stock Management",
        "📸 Shelf Check": "Shelf Check",
        "📈 Pricing Brain": "Pricing Brain",
        "⚠️ Quality Guard": "Quality Guard",
        "🧾 POS / Billing": "POS / Billing",
        "🚚 Smart Route Optimizer": "Smart Route Optimizer"
    }
    
    selected_label = st.radio("NAVIGATION", list(menu_options.keys()), label_visibility="collapsed")
    menu = menu_options[selected_label]
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="background: #FEF5E7; padding: 25px; border-radius: 20px; text-align: center;">
            <p style="color:#E67E22; font-weight:700; margin:0; font-size:1.1rem;">Your Smart Store</p>
            <p style="color:#7B8A8A; font-size:0.9rem; margin-top:10px;">AI tools to help you manage your grocery store easily and efficiently.</p>
        </div>
    """, unsafe_allow_html=True)

# --- Helper: Creative Metric ---
def render_creative_metric(label, value, icon="✧"):
    st.markdown(f"""
        <div class="creative-card metric-card">
            <div class="metric-icon-wrapper">{icon}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
        </div>
    """, unsafe_allow_html=True)

# --- 1. SHOP OVERVIEW ---
if menu == "Shop Overview":
    st.markdown("<h1 style='letter-spacing: -0.02em;'>Dashboard Overview</h1>", unsafe_allow_html=True)
    st.markdown('<div class="creative-card" style="padding: 15px 30px; margin-bottom: 40px;">', unsafe_allow_html=True)
    st.markdown("<p style='color: #1A1A1A; font-size: 1.1rem; margin: 0;'>Get a quick summary of your grocery store's daily performance, top-selling items, and stock alerts.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Data Fetching
    t_val, t_qty, l_stock = 0, 0, 0
    top_df = pd.DataFrame()
    conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
    if conn:
        try:
            r = pd.read_sql("SELECT SUM(quantity), SUM(total_amount) FROM retail_items", conn)
            t_qty, t_val = r.iloc[0,0] or 0, r.iloc[0,1] or 0
            l_stock = pd.read_sql("SELECT COUNT(*) FROM retail_items WHERE quantity < 10", conn).iloc[0,0]
            top_df = pd.read_sql("SELECT item_name, quantity FROM retail_items ORDER BY quantity DESC LIMIT 6", conn)
            conn.close()
        except: pass

    # Metric Row
    col1, col2, col3 = st.columns(3)
    with col1: render_creative_metric("Collection Size", f"{int(t_qty):,}", "✧")
    with col2: render_creative_metric("Market Worth", f"₹{int(t_val):,}", "◇")
    with col3: render_creative_metric("Critical Focus", l_stock, "◦")

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    c_left, c_right = st.columns([1.6, 1])
    
    with c_left:
        st.markdown('<div class="creative-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='font-family: Playfair Display; margin-bottom: 10px; color: var(--forest); font-size: 2rem;'>Inventory Sentiment</h3>", unsafe_allow_html=True)
        st.markdown("<div style='width: 50px; height: 1px; background: var(--gold); margin-bottom: 45px;'></div>", unsafe_allow_html=True)
        
        if not top_df.empty:
            fig = px.bar(
                top_df, x='item_name', y='quantity',
                color='quantity', 
                color_continuous_scale=['#FDFBF7', '#D4AF37', '#2C3E50']
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font_family="Outfit", margin=dict(l=0, r=0, t=10, b=0), height=480,
                coloraxis_showscale=False, xaxis_title="", yaxis_title="",
                xaxis={
                    'categoryorder':'total descending', 
                    'tickfont': {'color': '#7D8E7E', 'size': 12},
                    'showgrid': False
                },
                yaxis={
                    'tickfont': {'color': '#7D8E7E', 'size': 11},
                    'showgrid': True,
                    'gridcolor': 'rgba(44, 62, 80, 0.05)',
                    'zeroline': False
                },
                hoverlabel=dict(bgcolor="white", font_size=15, font_family="Outfit"),
                bargap=0.45,
                barcornerradius=25
            )
            fig.update_traces(marker_line_width=0, opacity=0.95, selector=dict(type='bar'))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else: st.info("No items found. Add some products in Stock Management.")
        st.markdown('</div>', unsafe_allow_html=True)

    with c_right:
        st.markdown('<div class="creative-card" style="height: 100%;">', unsafe_allow_html=True)
        st.markdown("<h3 style='margin-bottom: 20px;'>Store Updates</h3>", unsafe_allow_html=True)
        
        st.markdown("""
            <div class="insight-item" style="border-bottom: 1px solid #EAEAEA; padding-bottom: 15px; margin-bottom: 15px;">
                <span class="badge badge-warm" style="font-weight: bold;">Daily Note</span>
                <p style="color: #1A1A1A; margin-top: 10px; font-size: 1rem; line-height: 1.5;">
                    Milk and bread stocks are running low today. Consider ordering more before the evening rush.
                </p>
            </div>
            <div class="insight-item">
                <span class="badge badge-cool" style="font-weight: bold;">System Status</span>
                <p style="color: #1A1A1A; margin-top: 10px; font-size: 1rem; line-height: 1.5;">
                    All systems are running smoothly. Inventory numbers are up to date!
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Download Store Report"):
            st.toast("Generating your daily report...")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 2. AI ASSISTANT ---
elif menu == "AI Assistant":
    st.markdown("<h1>AI Assistant Manager</h1>", unsafe_allow_html=True)
    st.markdown('<div class="creative-card" style="padding: 15px 30px; margin-bottom: 40px;">', unsafe_allow_html=True)
    st.markdown("<p style='color: #1A1A1A; font-size: 1.1rem; margin: 0;'>Talk to your smart assistant. You can ask questions about your stock, sales, and products using your voice or by typing.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if "messages" not in st.session_state: st.session_state.messages = []
    
    # Message Display
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            if m["role"] == "assistant":
                st.markdown(f"<div style='font-family: Playfair Display; font-size: 1.2rem; color: var(--forest); margin-bottom: 12px;'>Observations:</div>", unsafe_allow_html=True)
            
            st.markdown(f"<div style='font-size: 1.05rem; line-height: 1.6;'>{m['content']}</div>", unsafe_allow_html=True)
            
            # Persistent Dataframe Display
            if "df" in m and m["df"] is not None and not m["df"].empty:
                st.markdown('<br>', unsafe_allow_html=True)
                st.markdown('<div class="creative-card" style="padding: 30px; border-radius: 8px;">', unsafe_allow_html=True)
                st.dataframe(m["df"], use_container_width=True, hide_index=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # Input Matrix
    c1, c2 = st.columns([1, 10])
    with c1:
        st.write("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🎙️", help="Voice Intuition", key="mic_btn"):
            v_text = listen_to_voice()
            if v_text: 
                st.session_state["v_query"] = v_text
                st.rerun()

    with c2:
        u_query = st.chat_input("Seek clarity on your collections...")
    
    final_q = u_query or st.session_state.get("v_query", "")
    if "v_query" in st.session_state: del st.session_state["v_query"]

    if final_q:
        st.session_state.messages.append({"role": "user", "content": final_q})
        with st.chat_message("user"):
            st.markdown(final_q)
            
        with st.chat_message("assistant"):
            with st.spinner("Refining thought..."):
                ans, df = handle_natural_query(final_q)
                st.markdown(f"<div style='font-family: Playfair Display; font-size: 1.2rem; color: var(--forest); margin-bottom: 15px;'>Observations:</div>", unsafe_allow_html=True)
                st.markdown(ans)
                if df is not None and not df.empty:
                    st.markdown('<br>', unsafe_allow_html=True)
                    st.markdown('<div class="creative-card" style="padding: 30px; border-radius: 8px;">', unsafe_allow_html=True)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                # Store text AND data for persistence
                st.session_state.messages.append({"role": "assistant", "content": ans, "df": df})
        st.rerun()

# --- 3. STOCK MANAGEMENT ---
elif menu == "Stock Management":
    st.markdown("<h1>Stock Management</h1>", unsafe_allow_html=True)
    
    st.markdown('<div class="creative-card" style="padding: 15px 30px; margin-bottom: 20px;">', unsafe_allow_html=True)
    st.markdown("<p style='color: #1A1A1A; font-size: 1.1rem; margin: 0;'>Easily manage your store inventory. Upload a PDF invoice from your supplier, and the system will read it and update your stock automatically.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="creative-card">', unsafe_allow_html=True)
    st.subheader("Invoice Digitization")
    st.write("Upload a supplier invoice to automatically update your inventory.")
    up_pdf = st.file_uploader("Drop PDF Invoice here", type=['pdf'], label_visibility="collapsed")
    if up_pdf and st.button("Sync Inventory"):
        with st.status("Reading your document...") as status:
            txt = extract_text_from_pdf(up_pdf)
            if txt:
                sql, _ = init_dynamic_db(txt)
                if sql:
                    data = extract_structured_data(txt, sql)
                    if data:
                        insert_dynamic_data(data)
                        status.update(label="✅ Inventory Updated", state="complete")
                        st.balloons()
                        st.dataframe(pd.DataFrame(data['items']), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>### Persistent Ledger")
    conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
    if conn:
        df_r = pd.read_sql("SELECT item_name, quantity, price, expiry_date FROM retail_items ORDER BY id DESC", conn)
        st.dataframe(df_r, use_container_width=True, hide_index=True)
        conn.close()

# --- 4. SHELF CHECK ---
elif menu == "Shelf Check":
    st.markdown("<h1>Shelf Check</h1>", unsafe_allow_html=True)
    st.markdown('<div class="creative-card" style="padding: 15px 30px; margin-bottom: 20px;">', unsafe_allow_html=True)
    st.markdown("<p style='color: #1A1A1A; font-size: 1.1rem; margin: 0;'>Take a photo of your shelves using your camera. The app will analyze the photo to check for missing items or messy shelves!</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="creative-card">', unsafe_allow_html=True)
    c_img = st.camera_input("Capture Shelf View")
    if c_img:
        with st.spinner("Analyzing physical shelf..."):
            audit = analyze_shelf_image(c_img.getvalue())
            if audit:
                for item in audit:
                    st.markdown(f"""
                        <div class="creative-card" style="border-left: 8px solid #E67E22;">
                            <h4 style="color:#E67E22; margin:0;">{item.get('item')}</h4>
                            <p style="margin:10px 0;"><b>Detected Issue:</b> {item.get('issue')}</p>
                            <span class="badge badge-cool">Action: {item.get('action')}</span>
                        </div>
                    """, unsafe_allow_html=True)
            else: st.success("Shelves look perfectly organized!")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. PRICING BRAIN ---
elif menu == "Pricing Brain":
    st.markdown("<h1>Pricing Brain</h1>", unsafe_allow_html=True)
    st.markdown('<div class="creative-card" style="padding: 15px 30px; margin-bottom: 20px;">', unsafe_allow_html=True)
    st.markdown("<p style='color: #1A1A1A; font-size: 1.1rem; margin: 0;'>Get smart price suggestions to maximize profits. Select the current weather or events, and the AI will recommend the best prices for your items.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="creative-card">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: cur_w = st.selectbox("Market Weather", ["Sunny", "Rainy", "Cold Wave", "Heat Wave"])
    with c2: cur_e = st.selectbox("Seasonal Events", ["None", "Festival", "Weekend Rush", "Local Holidays"])
    
    if st.button("Optimize Prices"):
        with st.spinner("AI Brainstorming..."):
            p_res = generate_dynamic_pricing(weather=cur_w, event=cur_e)
            if p_res:
                for p in p_res:
                    with st.expander(f"🔮 {p.get('item_name')} | Recommended: ₹{p.get('new_price')}"):
                        st.write(f"**Justification:** {p.get('reason')}")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. QUALITY GUARD ---
elif menu == "Quality Guard":
    st.markdown("<h1>Quality Guard</h1>", unsafe_allow_html=True)
    st.markdown('<div class="creative-card" style="padding: 15px 30px; margin-bottom: 20px;">', unsafe_allow_html=True)
    st.markdown("<p style='color: #1A1A1A; font-size: 1.1rem; margin: 0;'>Check for items that are expiring soon. The system will suggest smart discounts so you can sell them before they go bad.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    if st.button("Scan Lifecycle"):
        lifecycle = analyze_expiry_and_pricing()
        if not lifecycle.empty:
            for _, r in lifecycle.iterrows():
                st.markdown(f"""
                    <div class="creative-card" style="border-right: 8px solid #E67E22;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <h3 style="margin:0;">{r['item_name']}</h3>
                            <span class="badge badge-warm">⚠️ Expires: {r['expiry_date']}</span>
                        </div>
                        <p style="color:#7B8A8A; margin:15px 0;">{r['AI_Strategy']}</p>
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size:2rem; font-weight:700; color:#1A1A1A;">₹{r['Suggested_Price']}</span>
                            <span style="text-decoration:line-through; color:#BDC3C7;">Original: ₹{r['price']}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else: st.success("Everything is fresh and in perfect condition.")

# --- 7. POS / BILLING ---
elif menu == "POS / Billing":
    st.markdown("<h1>Billing Point</h1>", unsafe_allow_html=True)
    st.markdown('<div class="creative-card" style="padding: 15px 30px; margin-bottom: 30px;">', unsafe_allow_html=True)
    st.markdown("<p style='color: #1A1A1A; font-size: 1.1rem; margin: 0;'>Create bills for your customers quickly. Select items from your store, adjust quantities, and generate a final receipt.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    l_reg, r_bill = st.columns([1, 1])
    
    with l_reg:
        st.markdown('<div class="creative-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='margin-bottom: 30px; font-weight: 300; color: var(--forest);'>Collection Selection</h3>", unsafe_allow_html=True)
        conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
        if conn:
            all_items = pd.read_sql("SELECT item_name, price, quantity FROM retail_items", conn)
            sel_name = st.selectbox("Product Search", ["..."] + all_items['item_name'].tolist())
            if sel_name != "...":
                item_stat = all_items[all_items['item_name'] == sel_name].iloc[0]
                q_val = st.number_input("Quantity", 1, int(item_stat['quantity']), 1)
                st.write("<br>", unsafe_allow_html=True)
                if st.button("✧ Add to Collection"):
                    if "cart" not in st.session_state: st.session_state.cart = []
                    st.session_state.cart.append({"Name": sel_name, "Qty": q_val, "Rate": item_stat['price'], "Total": q_val * item_stat['price']})
                    st.toast(f"Added {sel_name} to Ledger")
            conn.close()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with r_bill:
        st.markdown('<div class="creative-card" style="border-top:2px solid var(--gold); background: #FCFAF9; padding: 40px;">', unsafe_allow_html=True)
        
        # Receipt Header
        st.markdown(f"""
            <div style='text-align: center; margin-bottom: 35px;'>
                <div style='border: 1px solid var(--forest); display: inline-block; padding: 8px 20px; letter-spacing: 0.3em; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; color: var(--forest);'>Atelier Registry</div>
                <div style='margin-top: 20px; font-size: 0.65rem; color: var(--clay); letter-spacing: 0.1em; text-transform: uppercase;'>
                    Ref. {time.strftime("%H%M%S")}-{os.getpid()} &nbsp; | &nbsp; {time.strftime("%d %b %Y")}
                </div>
            </div>
            <div style='border-top: 1px dotted rgba(44,62,80,0.2); margin-bottom: 30px;'></div>
        """, unsafe_allow_html=True)
        
        if "cart" in st.session_state and st.session_state.cart:
            for i in st.session_state.cart:
                st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:20px;'>
                        <div style='flex: 1;'>
                            <div style='font-family: Playfair Display; font-size: 1.15rem; color: var(--forest); line-height: 1.2;'>{i['Name']}</div>
                            <div style='font-size: 0.7rem; color: var(--clay); letter-spacing: 0.08em; margin-top: 4px;'>QTY: {i['Qty']} × ₹{i['Rate']:,}</div>
                        </div>
                        <div style='font-family: Outfit; font-weight: 600; color: var(--forest); font-size: 1.1rem;'>₹{i['Total']:,.2f}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            # Bottom Total Section
            st.markdown("<div style='border-top: 1px solid var(--gold); margin: 40px 0 25px 0; opacity: 0.2;'></div>", unsafe_allow_html=True)
            sum_t = sum(item['Total'] for item in st.session_state.cart)
            st.markdown(f"""
                <div style='display:flex; justify-content:space-between; align-items:baseline; margin-bottom:45px;'>
                    <div style='color: var(--clay); letter-spacing: 0.2em; font-size: 0.65rem; font-weight: 700; text-transform: uppercase;'>Final Valuation</div>
                    <div style='font-family: Playfair Display; font-size: 2.3rem; color: var(--forest); font-weight: 900; letter-spacing: -0.02em;'>₹{sum_t:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("Commit to Ledger", use_container_width=True):
                st.balloons(); st.session_state.cart = []; st.rerun()
        else:
            st.markdown("<p style='text-align:center; color: var(--clay); font-style: italic; padding: 60px 0; font-size: 0.9rem; opacity: 0.6;'>Your cart is empty. Add a product to start creating a bill.</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- 8. SMART ROUTE OPTIMIZER ---
elif menu == "Smart Route Optimizer":
    st.markdown("<h1>Smart Route Optimizer</h1>", unsafe_allow_html=True)
    st.markdown('<div class="creative-card" style="padding: 15px 30px; margin-bottom: 30px;">', unsafe_allow_html=True)
    st.markdown("<p style='color: #1A1A1A; font-size: 1.1rem; margin: 0;'>Plan the most efficient delivery routes for your grocery store. Save time and fuel by optimizing your delivery paths.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="creative-card">', unsafe_allow_html=True)
    st.markdown("<h3 style='margin-bottom: 15px;'>Route Planning & Logistics</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #1A1A1A; margin-bottom: 25px; line-height: 1.6;'>Our Smart Route Optimizer helps you manage multiple deliveries efficiently. By calculating the shortest and fastest paths considering real-time constraints, it ensures your store's deliveries reach customers fresh and on time.</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.image("https://images.unsplash.com/photo-1524661135-423995f22d0b?auto=format&fit=crop&q=80&w=600", caption="Optimize your delivery paths", use_container_width=True)
    with col2:
        st.image("https://images.unsplash.com/photo-1580674285054-bed31e145f59?auto=format&fit=crop&q=80&w=600", caption="Ensure timely and fresh deliveries", use_container_width=True)
        
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('''
        <div style="text-align: center;">
            <a href="https://smart-route-optimization.streamlit.app/" target="_blank" style="text-decoration: none;">
                <div style="background-color: var(--forest); color: #FFFFFF; padding: 18px 40px; border-radius: 4px; text-align: center; font-weight: 600; font-family: Outfit, sans-serif; display: inline-block; letter-spacing: 0.1em; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(44, 62, 80, 0.2);">
                    OPEN SMART ROUTE OPTIMIZER 🚀
                </div>
            </a>
        </div>
    ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True) # End main-content-wrapper
