
import os
import sys
from database import init_dynamic_db, insert_dynamic_data, extract_structured_data, create_connection
from processor import extract_text_from_pdf
from ai_features import analyze_expiry_and_pricing, handle_natural_query
import json
import pandas as pd

def process_single_pdf(file_path):
    """
    Existing logic to handle CLI processing of PDFs
    """
    print(f"--- Processing: {file_path} ---")
    
    try:
        with open(file_path, 'rb') as f:
            text_content = extract_text_from_pdf(f)
            
        if not text_content:
            print("Error: Could not extract text.")
            return

        print(f"Extracted {len(text_content)} chars.")
        
        # 1. DB Schema & Insert
        schema_sql, error_msg = init_dynamic_db(text_content)
        
        if schema_sql:
            data_dict = extract_structured_data(text_content, schema_sql)
            if data_dict:
                print(f"Extracted Data: {json.dumps(data_dict, indent=2)}")
                insert_dynamic_data(data_dict)
                print("✅ Data inserted successfully.")
                
                # 2. RUN AI FEATURES AUTOMATICALLY
                print("\n🧠 RUNNING AI ANALYTICS...")
                
                # Feature 3: Expiry Check
                expiry_df = analyze_expiry_and_pricing()
                if not expiry_df.empty:
                    print(f"⚠️ Warning: Found {len(expiry_df)} expiring items!")
                    print(expiry_df[['item_name', 'expiry_date', 'AI_Strategy', 'Suggested_Price']])
                else:
                    print("✅ No immediate expiry risks.")
                    
            else:
                print("Failed to extract structured data.")
        else:
            print(f"Schema Error: {error_msg}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        process_single_pdf(sys.argv[1])
    else:
        # Mini Interactive mode for testing NLP
        print("\n--- RetailWise AI Terminal ---")
        param = input("Enter PDF path OR type 'chat' to test AI Assistant: ").strip()
        
        if param.lower() == 'chat':
            while True:
                q = input("\nAsk AI (or 'exit'): ")
                if q.lower() == 'exit': break
                resp, df = handle_natural_query(q)
                print(f"AI: {resp}")
                if df is not None:
                    print(df)
        elif param:
            # Remove quotes
            if param.startswith('"') and param.endswith('"'):
                param = param[1:-1]
            process_single_pdf(param)
