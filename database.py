import mysql.connector
import json
import re
from mysql.connector import Error
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# Initialize Groq client for schema generation
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

def create_connection(db_name=None):
    """Create a database connection to the MySQL database"""
    connection = None
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=db_name if db_name else None
        )
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection

def generate_table_schema_from_text(text):
    """
    Uses AI to analyze the PDF text and generate a suitable MySQL CREATE TABLE statement.
    """
    # Truncate text for prompt
    truncated_text = text[:10000]

    system_prompt = "You are an expert database administrator. Your task is to design a MySQL table schema based on the content of a document."
    
    user_prompt = f"""
    Analyze the following text from a retail document (invoice, receipt, or stock list).
    
    1. Identify if the document contains a list of items with details like 'Item Name', 'Quantity', 'Price', 'Total', etc.
    2. Propose a MySQL `CREATE TABLE` statement for a table named `retail_items`.
    3. The schema MUST include:
       - `id` INT AUTO_INCREMENT PRIMARY KEY
       - `item_name` VARCHAR(255) (or similar inferred name)
       - `quantity` INT (or DECIMAL if applicable)
       - `price` DECIMAL(10,2)
       - `total_amount` DECIMAL(10,2)
       - `manufacturing_date` DATE (if available)
       - `expiry_date` DATE (if available)
       - `extracted_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    4. Return ONLY the raw SQL `CREATE TABLE` statement. No markdown, no comments.
    
    Text Content:
    {truncated_text}
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        content = chat_completion.choices[0].message.content.strip()
        print(f"DEBUG: Raw AI Response:\n{content}\n-------------------")
        
        # Extract SQL using Regex
        # 1. Look for markdown code block
        code_block = re.search(r"```sql\s*([\s\S]*?)\s*```", content, re.IGNORECASE)
        if code_block:
            return code_block.group(1).strip(), None
            
        # 2. Look for explicit CREATE TABLE statement
        sql_match = re.search(r"CREATE TABLE\s+[\s\S]+?;", content, re.IGNORECASE)
        if sql_match:
            return sql_match.group(0).strip(), None
            
        # 3. Fallback: messy cleanup
        cleaned = content.replace("```sql", "").replace("```", "").strip()
        return cleaned, None

    except Exception as e:
        print(f"Error generating schema: {e}")
        return None, str(e)

def extract_structured_data(text, table_schema):
    """
    Uses AI to extract data from the text that matches the generated schema.
    """
    truncated_text = text[:15000]
    
    system_prompt = "You are a data extraction specialist. Output valid JSON only."
    
    user_prompt = f"""
    Based on the text below, extract a LIST of items that match this MySQL table schema:
    {table_schema}
    
    Return a valid JSON object with a single key "items" containing an array of objects.
    Example format:
    {{
        "items": [
            {{"item_name": "Apple", "quantity": 10, "price": 1.50, "manufacturing_date": "2023-10-01", "expiry_date": "2023-11-01"}},
            {{"item_name": "Banana", "quantity": 5, "price": 0.80, "manufacturing_date": null, "expiry_date": null}}
        ]
    }}
    
    - Map the text content to the column names in the schema exactly.
    - Remove currency symbols ($) and commas from numbers.
    - If a field is missing, use null.
    
    Text:
    {truncated_text}
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"Error extracting data: {e}")
        return None

def init_dynamic_db(text_content):
    """
    Analyzes the text, creates a tailored table, and returns the table name.
    """
    db_name = os.getenv("DB_NAME", "retailwise_db")
    
    # 1. Create DB if not exists
    conn = create_connection() # Connect to server only
    if not conn:
        return None, "Connection Failed: Could not connect to MySQL server. Check your .env credentials."

    cursor = conn.cursor()
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        conn.close()
    except Error as e:
        print(f"DB Creation Error: {e}")
        return None, f"DB Creation Error: {e}"

    # 2. Convert text to Schema
    print("🤖 AI is designing the database schema based on your PDF...")
    create_table_sql, error = generate_table_schema_from_text(text_content)
    
    if not create_table_sql:
        print(f"Failed to generate schema. Error: {error}")
        return None, f"AI Schema Error: {error}"

    print(f"Generated Schema:\n{create_table_sql}")

    # 3. Create Table
    conn = create_connection(db_name)
    if conn:
        try:
            cursor = conn.cursor()
            # Drop old table to allow new schema for this demo
            cursor.execute("DROP TABLE IF EXISTS retail_items") 
            cursor.execute(create_table_sql)
            conn.commit()
            print("✅ Table 'retail_items' created successfully.")
            return create_table_sql, None
        except Error as e:
            print(f"Table Creation Error: {e}")
            return None, f"Table Creation Error: {e}. SQL: {create_table_sql}"
        finally:
            conn.close()
    
    return None, f"Could not connect to database '{db_name}'."

def insert_dynamic_data(data_dict):
    """
    Inserts the extracted JSON data into the retail_items table.
    """
    conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # The data_dict now contains {"items": [...]}
        items_list = data_dict.get("items", [])
        
        if not items_list:
            print("No items found to insert.")
            return False

        print(f"Inserting {len(items_list)} items into database...")

        for item in items_list:
            # Filter out keys that might not be in the schema if AI hallucinates extra fields
            # Ideally, we should check against the schema, but relying on AI's consistency for now.
            # A safer way is to assume AI matched schema cols.
            
            columns = ', '.join(item.keys())
            placeholders = ', '.join(['%s'] * len(item))
            sql = f"INSERT INTO retail_items ({columns}) VALUES ({placeholders})"
            values = list(item.values())
            
            # Identify NULLs or invalid dates if necessary, but MySQL driver handles None as NULL
            cursor.execute(sql, values)
            
        conn.commit()
        print("✅ All items inserted successfully.")
        return True
    except Error as e:
        print(f"Insertion Error: {e}")
        return False
    finally:
        conn.close()
