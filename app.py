
import streamlit as st
import pandas as pd
from database import init_dynamic_db, insert_dynamic_data, extract_structured_data, create_connection
from processor import extract_text_from_pdf, extract_keywords_ai
from ai_features import handle_natural_query, get_restock_suggestions, analyze_expiry_and_pricing, listen_to_voice, generate_dynamic_pricing, analyze_shelf_image
import json
import os
import time

# --- Setup ---
st.set_page_config(page_title="RetailWise - AI Shop Assistant", page_icon="🛍️", layout="wide")

# Initialize DB connection on first load
if "conn_checked" not in st.session_state:
    conn = create_connection()
    if conn:
        st.session_state["conn_checked"] = True
        conn.close()

# --- Custom CSS ---
st.markdown("""
<style>
    .stApp { background-color: #f7f9fc; }
    .feature-card {
        background: white; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px;
    }
    .metric-value { font-size: 2rem; font-weight: bold; color: #2E86C1; }
    .status-expired { color: #E74C3C; font-weight: bold; }
    .status-ok { color: #27AE60; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3081/3081559.png", width=50)
    st.title("RetailWise AI")
    st.caption("Empowering Local Kirana Stores")
    
    menu = st.radio("Navigation", [
        "🏠 Dashboard", 
        "🎤 Smart Assistant", 
        "📦 Inventory & Upload", 
        "📸 Shelf Auditor",
        "📈 Dynamic Pricing", 
        "⚠️ Expiry & Pricing", 
        "🧾 Quick Invoice"
    ])
    
    st.divider()
    st.info("💡 **Did you know?**\nUse the Smart Assistant to ask: *'Show me all expiring chips'*")

# --- 1. DASHBOARD ---
if menu == "🏠 Dashboard":
    st.title("Store Overview 📊")
    st.markdown("### Welcome back, Shopkeeper!")
    
    # Get Stats
    conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
    total_val = 0
    if conn:
        try:
            total_items = pd.read_sql("SELECT COUNT(*) FROM retail_items", conn).iloc[0,0]
            low_stock = pd.read_sql("SELECT COUNT(*) FROM retail_items WHERE quantity < 10", conn).iloc[0,0]
            expiring_soon = pd.read_sql("SELECT COUNT(*) FROM retail_items WHERE expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)", conn).iloc[0,0]
            total_val = pd.read_sql("SELECT SUM(total_amount) FROM retail_items", conn).iloc[0,0] or 0
            
            # Data for charts
            top_items_qty = pd.read_sql("SELECT item_name, quantity FROM retail_items ORDER BY quantity DESC LIMIT 5", conn)
            top_items_val = pd.read_sql("SELECT item_name, total_amount FROM retail_items ORDER BY total_amount DESC LIMIT 5", conn)
            
            conn.close()
        except:
            total_items, low_stock, expiring_soon = 0, 0, 0
            top_items_qty, top_items_val = pd.DataFrame(), pd.DataFrame()

    # -- Key Metrics Row --
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="feature-card"><h3>📦 Total Items</h3><p class="metric-value">{total_items}</p></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="feature-card"><h3>💰 Inventory Value</h3><p class="metric-value">₹{int(total_val):,}</p></div>""", unsafe_allow_html=True)
    with c3:
        color_cls = "status-expired" if low_stock > 0 else "status-ok"
        st.markdown(f"""<div class="feature-card"><h3>📉 Low Stock</h3><p class="metric-value {color_cls}">{low_stock}</p></div>""", unsafe_allow_html=True)
    with c4:
        color_cls = "status-expired" if expiring_soon > 0 else "status-ok"
        st.markdown(f"""<div class="feature-card"><h3>⏳ Expiring Soon</h3><p class="metric-value {color_cls}">{expiring_soon}</p></div>""", unsafe_allow_html=True)

    st.divider()

    # -- Charts Row --
    st.subheader("📈 Business Insights")
    chart_c1, chart_c2 = st.columns(2)
    
    with chart_c1:
        st.write("**Top 5 Items (by Quantity)**")
        if not top_items_qty.empty:
            st.bar_chart(top_items_qty.set_index('item_name'))
        else:
            st.info("No data available.")

    with chart_c2:
        st.write("**High Value Stock**")
        if not top_items_val.empty:
            st.bar_chart(top_items_val.set_index('item_name'))
        else:
            st.info("No data available.")
            
    st.divider()
    
    # -- Restock Genius Feature --
    st.subheader("⚡ Restock Genius Suggestions")
    suggestions = get_restock_suggestions(threshold=10)
    
    if not suggestions.empty:
        with st.expander("🚨 View Items Needing Restock", expanded=True):
            st.dataframe(
                suggestions[['item_name', 'quantity', 'price', 'Suggested_Action', 'Est_Restock_Cost']], 
                use_container_width=True
            )
            if st.button("🛒 1-Click Order (Simulated)"):
                st.success("Orders sent to Local Wholesalers! (Feature simulated)")
    else:
        st.success("✅ Stock levels are healthy! No immediate restock needed.")

# --- 2. SMART ASSISTANT (NLP) ---
elif menu == "🎤 Smart Assistant":
    st.title("🤖 AI Shop Assistant")
    st.write("Ask anything about your stock naturally. Supports partial matches and simple logic.")
    
    col_input, col_mic = st.columns([6, 1])
    
    with col_mic:
        st.write("") # Spacer
        st.write("") 
        if st.button("🎤", help="Click to Speak"):
            voice_text = listen_to_voice()
            if voice_text:
                # Update query and rerun to process
                st.session_state["voice_query"] = voice_text
                st.rerun()

    # Check for voice input in session state
    initial_value = st.session_state.get("voice_query", "")
    # Clear it after reading so it doesn't stick forever if we edit it
    if "voice_query" in st.session_state:
        del st.session_state["voice_query"]

    with col_input:
        query = st.chat_input("Ask: 'Show milk stock'...", key="chat_input")
        # If we had voice input, we manually inject it as if user typed it? 
        # Streamlit chat_input can't be set programmatically easily in same run without hack.
        # Workaround: Use a session state variable to display it or process it directly.
    
    # Logic to handle Voice Query falling back to chat flow
    final_query = None
    if query:
        final_query = query
    elif initial_value:
        final_query = initial_value

    # Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if final_query:
        # Display User Msg
        with st.chat_message("user"):
            st.markdown(final_query)
        st.session_state.messages.append({"role": "user", "content": final_query})

        # Process with AI
        with st.spinner("Thinking..."):
            response_text, df_result = handle_natural_query(final_query)
        
        # Display AI Msg
        with st.chat_message("assistant"):
            st.markdown(response_text)
            if df_result is not None and not df_result.empty:
                st.dataframe(df_result)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})


# --- 3. INVENTORY & UPLOAD (Original Feature) ---
elif menu == "📦 Inventory & Upload":
    st.title("📄 Upload Invoice / Update Stock")
    
    uploaded_file = st.file_uploader("Upload Supplier Invoice (PDF)", type=['pdf'])
    
    if uploaded_file is not None:
        if st.button("🚀 Process & Add to Inventory"):
            with st.spinner("Reading & Installing..."):
                # Pass file-like object directly
                text_content = extract_text_from_pdf(uploaded_file)
                
                if text_content and len(text_content) > 10:
                    st.success("Text extracted successfully!")
                    
                    # Auto-Schema & Extract
                    with st.status("🤖 AI is designing database schema...", expanded=True) as status:
                        schema_sql, error_msg = init_dynamic_db(text_content)
                        
                        if schema_sql:
                            data_dict = extract_structured_data(text_content, schema_sql)
                            
                            if data_dict and "items" in data_dict:
                                if insert_dynamic_data(data_dict):
                                    st.success(f"✅ Automatically added {len(data_dict['items'])} items to inventory!")
                                    st.dataframe(pd.DataFrame(data_dict['items']))
                                else:
                                    st.error("Failed to save to DB.")
                            else:
                                st.error("Could not extract structured data.")
                        else:
                            st.error(f"Schema Error: {error_msg}")
                            status.update(label="❌ AI Schema Generation Failed", state="error")
                else:
                    st.error("Could not extract text from PDF.")

    st.divider()
    st.subheader("Current Inventory")
    conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
    if conn:
        df = pd.read_sql("SELECT * FROM retail_items ORDER BY id DESC", conn)
        st.dataframe(df, use_container_width=True)
        conn.close()

# --- 4. EXPIRY & PRICING ---
elif menu == "⚠️ Expiry & Pricing":
    st.title("📉 Smart Pricing Engine")
    st.markdown("AI suggests discounts to clear expiring stock and maximize revenue.")
    
    if st.button("🔄 Analyze Shelf Life"):
        with st.spinner("AI checking dates & market prices..."):
            df_expiry = analyze_expiry_and_pricing() # No arguments now, handled internally
            
            if not df_expiry.empty:
                st.write("### 🏷️ Recommended Discounts")
                
                # Stylized Display
                for _, row in df_expiry.iterrows():
                    with st.expander(f"🔴 {row['item_name']} (Exp: {row['expiry_date']})", expanded=True):
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Original Price", f"₹{row['price']}")
                        c2.metric("AI Suggested Price", f"₹{row['Suggested_Price']}")
                        c3.error(row['AI_Strategy'])
                        
                        if st.button(f"Apply Price ₹{row['Suggested_Price']}", key=f"btn_{row['id']}"):
                            st.toast(f"Price updated for {row['item_name']}!")
            else:
                st.success("✅ Shelf Analysis Complete: No items found expiring within the next 30 days.")


# --- 5. SHELF AUDITOR ---
elif menu == "📸 Shelf Auditor":
    st.title("📸 AI Shelf Auditor")
    st.markdown("Snap a picture of your physical shelf via your mobile camera or upload an image. AI will detect missing or misplaced stock.")
    
    shelf_image = st.camera_input("Take a picture of the shelf")
    
    if shelf_image is not None:
        with st.spinner("Analyzing shelf with AI Vision..."):
            image_bytes = shelf_image.getvalue()
            issues = analyze_shelf_image(image_bytes)
            
            if issues:
                st.subheader("🚨 Shelf Insights")
                for issue in issues:
                    st.error(f"**Item:** {issue.get('item', 'Unknown')}\\n\\n**Issue:** {issue.get('issue', 'Issue detected')}\\n\\n**Action:** {issue.get('action', 'Check shelf')}")
            else:
                st.success("✅ Shelf looks perfect. No issues found.")

# --- 6. DYNAMIC PRICING ---
elif menu == "📈 Dynamic Pricing":
    st.title("📈 AI Dynamic Pricing Engine")
    st.markdown("Adjust prices dynamically based on weather, local events, and competitor data.")
    
    col1, col2 = st.columns(2)
    with col1:
        weather_opt = st.selectbox("Current Weather", ["Sunny", "Rainy", "Cold Wave", "Heat Wave"])
    with col2:
        event_opt = st.selectbox("Local Event", ["None", "Festival Season", "Cricket Match", "School Reopening"])
        
    if st.button("🚀 Analyze Market Context"):
        with st.spinner("AI checking market context..."):
            pricing_suggestions = generate_dynamic_pricing(weather=weather_opt, event=event_opt)
            
            if pricing_suggestions:
                st.write("### 🏷️ Dynamic Price Adjustments")
                for item in pricing_suggestions:
                    with st.expander(f"🔄 {item.get('item_name')} | Old: ₹{item.get('original_price')} -> New: ₹{item.get('new_price')}", expanded=True):
                        st.info(f"**Reason:** {item.get('reason')}")
            else:
                st.warning("⚠️ Could not generate dynamic pricing. Make sure you have items in inventory.")

# --- 7. QUICK INVOICE ---
elif menu == "🧾 Quick Invoice":
    st.title("⚡ POS / Invoice Builder")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Select Items")
        conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
        if conn:
            # Dropdown for selecting items
            items_df = pd.read_sql("SELECT id, item_name, price, quantity FROM retail_items", conn)
            item_list = items_df['item_name'].tolist()
            
            selected_item_name = st.selectbox("Search Item", ["Select..."] + item_list)
            
            if selected_item_name != "Select...":
                item_details = items_df[items_df['item_name'] == selected_item_name].iloc[0]
                st.info(f"Price: ₹{item_details['price']} | Stock: {item_details['quantity']}")
                
                qty = st.number_input("Quantity", min_value=1, max_value=int(item_details['quantity']))
                
                if st.button("Add to Bill"):
                    if "cart" not in st.session_state:
                         st.session_state.cart = []
                    st.session_state.cart.append({
                        "Item": selected_item_name,
                        "Qty": qty,
                        "Price": item_details['price'],
                        "Total": qty * item_details['price']
                    })
                    st.success("Added!")

    with col2:
        st.subheader("🛒 Current Bill")
        if "cart" in st.session_state and st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.dataframe(cart_df, hide_index=True)
            
            total = cart_df['Total'].sum()
            st.metric("Grand Total", f"₹{total}")
            
            if st.button("🖨️ Print Invoice"):
                # Update DB and decrease stock
                conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
                if conn:
                    cursor = conn.cursor()
                    try:
                        for item in st.session_state.cart:
                            item_name = item['Item']
                            qty = int(item['Qty'])
                            cursor.execute("UPDATE retail_items SET quantity = quantity - %s WHERE item_name = %s", (qty, item_name))
                        conn.commit()
                        st.success("Invoice Generated! Stock updated in inventory & SMS Sent to Customer! (Simulated)")
                    except Exception as e:
                        st.error(f"Failed to update stock: {e}")
                    finally:
                        conn.close()
                st.balloons()
                st.session_state.cart = [] # Reset
                time.sleep(1)
                st.rerun()
        else:
            st.write("Cart is empty.")
