
from groq import Groq
import os
import pandas as pd
from datetime import datetime, timedelta
import json
from database import create_connection
import speech_recognition as sr
import streamlit as st

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- FEATURE 1: SMART SEARCH (NLP to SQL) ---
def handle_natural_query(user_query):
    """
    Converts natural language to SQL, executes it, and explains results.
    """
    system_prompt = """
    You are a MySQL expert assisting a shopkeeper. 
    The table is `retail_items`. Columns: id, item_name, quantity, price, total_amount, manufacturing_date, expiry_date, extracted_at.
    
    1. Convert the User's question into a standard SQL query.
    2. Return ONLY the SQL query. No markdown, no explanations.
    3. Use LIKE for fuzzy matching (e.g., '%butter%').
    4. Handle dates: CURDATE() for today.
    """
    
    try:
        # 1. Get SQL from AI
        chat = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0
        )
        sql_query = chat.choices[0].message.content.strip().replace("```sql", "").replace("```", "")
        
        # 2. Execute SQL
        conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
        if not conn:
            return "❌ Database connection failed.", None
            
        df = pd.read_sql(sql_query, conn)
        conn.close()
        
        # 3. Explain Answer using AI
        if df.empty:
            return f"I couldn't find any results for that in the current collection. (Query: `{sql_query}`)", df
            
        # Generating a curation summary
        results_summary = df.to_string(index=False)
        summary_prompt = f"""
        Summarize the following data in a conversational, elegant boutique style. 
        The User asked: "{user_query}"
        The Data: {results_summary}
        
        Provide a concise, sophisticated observation. Mention specific values found. 
        Example: "Our records reflect that the current valuation for [item] is [price] with [quantity] available in carefully maintained storage."
        No generic 'Based on your request' introductions. 
        """
        
        summary_chat = client.chat.completions.create(
            messages=[{"role": "user", "content": summary_prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.4
        )
        
        explanation = summary_chat.choices[0].message.content.strip()
        return explanation, df
        
    except Exception as e:
        return f"I encountered a slight disturbance in the digital ledger. Error: {str(e)}", None

# --- VOICE ASSISTANT FEATURE ---
def listen_to_voice():
    """
    Listens to microphone input and converts to text.
    Returns: Recognized Text or None
    """
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            st.toast("🎤 Listening... Speak now!", icon="👂")
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            # Listen
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            st.toast("Processing voice...", icon="🔄")
            text = recognizer.recognize_google(audio)
            return text
            
    except sr.WaitTimeoutError:
        st.error("No speech detected. Try again.")
        return None
    except sr.RequestError:
        st.error("Could not request results from Google Speech Recognition service.")
        return None
    except Exception as e:
        st.error(f"Microphone Error: {e}")
        return None

# --- FEATURE 2: RESTOCK GENIUS ---
def get_restock_suggestions(threshold=10):
    """
    Identifies low stock items and suggests local suppliers (mocked).
    """
    conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
    if not conn:
        return pd.DataFrame()
        
    query = f"SELECT * FROM retail_items WHERE quantity < {threshold} ORDER BY quantity ASC"
    df = pd.read_sql(query, conn)
    conn.close()
    
    if not df.empty:
        # Mocking AI Supplier Logic
        df['Suggested_Action'] = "Order from Local Wholesaler A"
        df['Est_Restock_Cost'] = df['quantity'].apply(lambda x: (threshold - x) * 100) # Dummy logic
        
    return df

# --- FEATURE 3 & 5: EXPIRY AI & DYNAMIC PRICING ---
def analyze_expiry_and_pricing():
    """
    Finds expiring items and suggests dynamic pricing discounts.
    """
    conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
    if not conn:
        return pd.DataFrame()
    
    # Get items expiring in next 30 days
    # Note: Using python for date logic to be safe across SQL versions if needed, but SQL is faster
    query = "SELECT * FROM retail_items WHERE expiry_date IS NOT NULL ORDER BY expiry_date ASC"
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        return df

    # Logic
    today = datetime.now().date()
    
    def calculate_deal(row):
        expiry_val = row['expiry_date']
        
        # Handle None/NaT
        if pd.isna(expiry_val) or not expiry_val:
            return "Standard Price", row['price']
            
        # Ensure date object
        try:
            if isinstance(expiry_val, str):
                expiry_dt = datetime.strptime(expiry_val, "%Y-%m-%d").date()
            elif hasattr(expiry_val, 'date'): # Datetime/Timestamp
                expiry_dt = expiry_val.date()
            else: # Date object
                expiry_dt = expiry_val
        except Exception:
             return "Invalid Date Format", row['price']

        days_left = (expiry_dt - today).days
        
        if days_left < 0:
            return "⚠️ EXPIRED - REMOVE", 0
        elif days_left <= 7:
            return "🔥 50% OFF (Clearance)", round(row['price'] * 0.5, 2)
        elif days_left <= 30:
            return "🏷️ 15% OFF (Near Expiry)", round(row['price'] * 0.85, 2)
        else:
            return "✅ Standard Price", row['price']

    # Apply Logic
    deal_data = df.apply(calculate_deal, axis=1, result_type='expand')
    df['AI_Strategy'] = deal_data[0]
    df['Suggested_Price'] = deal_data[1]
    
    # Filter for interesting ones (Expired or Discounted)
    mask = df['AI_Strategy'] != "Standard Price"
    return df[mask]

# --- FEATURE 6: INVOICE BUILDER (Helpers) ---
def get_all_inventory():
    conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
    if conn:
        df = pd.read_sql("SELECT item_name, price, quantity FROM retail_items", conn)
        conn.close()
        return df
    return pd.DataFrame()

# --- FEATURE 4: AI SHELF AUDITOR (COMPUTER VISION) ---
import base64

def analyze_shelf_image(image_bytes):
    """
    Uses AI vision to detect empty spots or misplaced items from a shelf image.
    """
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        system_prompt = "You are a retail shelf auditor AI. Find empty spots and misplaced items."
        user_prompt = "Analyze this store shelf. Identify empty spots or misplaced items. Return JSON: {'issues': [{'item': 'Chips', 'issue': 'Empty spot', 'action': 'Restock'}]}"
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            model="llama-3.2-90b-vision-preview",
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        res = json.loads(chat_completion.choices[0].message.content)
        return res.get("issues", [])
    except Exception as e:
        # Provide a mock response in case of API limitations/no vision model
        import time
        time.sleep(2)
        return [
            {"item": "Amul Butter", "issue": "Out of Stock (Empty spot found)", "action": "Order 10 units"},
            {"item": "Lays Chips", "issue": "Misplaced (Found in Drinks aisle)", "action": "Move to Snacks"},
            {"item": "Error detail (Simulation Mode)", "issue": str(e), "action": "API did not support vision request."}
        ]

# --- FEATURE 5 (Update): PURE DYNAMIC PRICING ENGINE ---
def generate_dynamic_pricing(weather="Sunny", event="None"):
    """
    Predicts dynamic prices based on context like weather and local events.
    """
    conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
    if not conn:
        return []
    
    query = "SELECT item_name, price, quantity FROM retail_items LIMIT 25"
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        return []

    items_list = df.to_dict(orient='records')
    
    system_prompt = "You are an AI Dynamic Pricing Engine for a local retail store."
    user_prompt = f"""
    Weather: {weather}
    Local Event: {event}
    
    Calculate dynamic pricing adjustments for the following items based on the context provided:
    {json.dumps(items_list)}
    
    Return ONLY a JSON object in this format:
    {{"prices": [{{"item_name": "...", "original_price": 100, "new_price": 120, "reason": "High demand due to rain (+20%)"}}]}}
    Keep the items matching exactly. Return the updated prices array.
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        res = json.loads(chat_completion.choices[0].message.content)
        return res.get("prices", [])
    except Exception as e:
        return []
