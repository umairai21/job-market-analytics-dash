import os
import requests
import pandas as pd
import time
from dotenv import load_dotenv
from transform_jobs import clean_job_data

load_dotenv()
ADZUNA_APP_ID = os.getenv('ADZUNA_APP_ID')
ADZUNA_APP_KEY = os.getenv('ADZUNA_APP_KEY')

# Notice we added 'page_number' as a parameter
def fetch_jobs_page(country_code, search_query, page_number):
    url = f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/{page_number}"
    
    params = {
        'app_id': ADZUNA_APP_ID,
        'app_key': ADZUNA_APP_KEY,
        'what': search_query,
        'results_per_page': 50,
        'content-type': 'application/json'
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    print("Starting deep extraction for UK data jobs...")
    
    all_dataframes = []
    page = 1
    max_pages = 20 # Will pull up to 1,000 jobs. Increase this later if you want more!
    
    while page <= max_pages:
        print(f"-> Fetching page {page}...")
        try:
            raw_data = fetch_jobs_page('gb', 'data', page)
            results = raw_data.get('results', [])
            
            # If the API returns an empty list, we've reached the end of all available jobs
            if not results:
                print("No more jobs found. Ending extraction.")
                break
                
            df_page = clean_job_data(raw_data)
            all_dataframes.append(df_page)
            
            page += 1
            # CRITICAL: Pause for 2 seconds to avoid getting banned for spamming the API
            time.sleep(2) 
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
            
    # Combine all the pages into one massive table
    if all_dataframes:
        master_df = pd.concat(all_dataframes, ignore_index=True)
        csv_path = 'uk_massive_job_data.csv'
        master_df.to_csv(csv_path, index=False)
        print(f"\nSuccess! Saved {len(master_df)} jobs to {csv_path}")
    else:
        print("No data retrieved.")