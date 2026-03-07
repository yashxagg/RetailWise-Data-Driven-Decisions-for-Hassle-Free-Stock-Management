
import os
import pandas as pd
from database import create_connection

def check_price_status():
    conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
    if not conn:
        print("DB Connection Failed")
        return

    try:
        # Check explicit columns
        cursor = conn.cursor()
        cursor.execute("DESCRIBE retail_items")
        columns = [row[0] for row in cursor.fetchall()]
        print(f"ALL COLUMNS: {columns}")
        
        if 'price' in columns:
            print("✅ 'price' column exists in schema.")
            # Check values
            df = pd.read_sql("SELECT price FROM retail_items WHERE price IS NOT NULL LIMIT 5", conn)
            print(f"Sample Prices:\n{df}")
            if df.empty:
                print("⚠️ Price column exists but all values are NULL.")
        else:
            print("❌ 'price' column DOES NOT EXIST in schema.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_price_status()
