import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load secret database credentials from .env
load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'job_market_db')

def load_data_to_db(df, table_name='uk_job_postings'):
    """
    Connects to PostgreSQL and safely appends the dataframe to the specified table.
    """
    try:
        # 1. Build the connection string (The Bridge)
        engine_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(engine_url)
        
        print(f"Connecting to local PostgreSQL database '{DB_NAME}'...")
        
        # 2. Push the data
        # if_exists='append' ensures we add new jobs on top of old ones every week
        # index=False prevents pandas from saving useless row numbers (0, 1, 2...)
        df.to_sql(table_name, con=engine, if_exists='append', index=False)
        
        print(f"Success! {len(df)} rows securely loaded into the '{table_name}' table.")
        
    except Exception as e:
        print(f"Database insertion failed: {e}")
        print("\nTIP: Is your PostgreSQL server running? Did you create 'job_market_db' in pgAdmin?")

if __name__ == "__main__":
    print("Initializing Database Load Process...")
    
    # We will point it directly at the CSV you generated in the last step
    csv_file = 'uk_massive_job_data.csv'
    
    if os.path.exists(csv_file):
        df_to_load = pd.read_csv(csv_file)
        load_data_to_db(df_to_load)
    else:
        print(f"Error: Could not find {csv_file}. Please check the file name.")