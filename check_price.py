
import os
import pandas as pd
from database import create_connection

def check_schema():
    conn = create_connection(os.getenv("DB_NAME", "retailwise_db"))
    if not conn:
        print("Connection failed")
        return

    try:
        cursor = conn.cursor()
        cursor.execute("DESCRIBE retail_items")
        columns = [row[0] for row in cursor.fetchall()]
        print(f"Columns in DB: {columns}")
        
        # Also check data sample to see if price is just all nulls
        try:
            df = pd.read_sql("SELECT * FROM retail_items LIMIT 5", conn)
            print("\nData Sample:")
            print(df)
        except Exception as e:
            print(f"Error reading data: {e}")

    except Exception as e:
        print(f"Error checking schema: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_schema()
