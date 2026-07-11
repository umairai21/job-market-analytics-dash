import pandas as pd

def clean_job_data(raw_json_data):
    job_listings = raw_json_data.get('results', [])
    cleaned_jobs = []
    
    for job in job_listings:
        title = job.get('title', 'Unknown')
        title_lower = title.lower()
        
        # --- 1. THE BOUNCER (Filter out the noise) ---
        if 'data entry' in title_lower or 'administrator' in title_lower:
            continue
            
        # --- 2. DYNAMIC CATEGORIZATION ---
        if 'analyst' in title_lower or 'analytics' in title_lower: 
            role_category = 'Data Analyst'
        elif 'engineer' in title_lower: 
            role_category = 'Data Engineer'
        elif 'scient' in title_lower: 
            role_category = 'Data Scientist'
        elif 'machine learning' in title_lower or 'ml ' in title_lower: 
            role_category = 'ML Engineer'
        elif 'bi ' in title_lower or 'business intelligence' in title_lower: 
            role_category = 'BI Developer'
        elif 'data' in title_lower: 
            role_category = 'Data Management/Other' 
        else:
            continue 
            
        # --- 3. METADATA EXTRACTION ---
        contract_time = job.get('contract_time', 'Not Specified')
        contract_type = job.get('contract_type', 'Not Specified')
        
        # Extract the posted date
        # Slicing [:10] turns '2026-07-11T18:07:39Z' into '2026-07-11'
        posted_date_raw = job.get('created', 'Not Specified')
        posted_date = posted_date_raw[:10] if posted_date_raw != 'Not Specified' else 'Not Specified'
        
        company = job.get('company', {}).get('display_name', 'Unknown')
        location_areas = job.get('location', {}).get('area', [])
        city = location_areas[-1] if location_areas else 'Unknown'
        salary_min = job.get('salary_min')
        salary_max = job.get('salary_max')
        
        job_record = {
            'posted_date': posted_date,
            'role_category': role_category,
            'job_title': title,
            'contract_time': contract_time,
            'contract_type': contract_type,
            'company_name': company,
            'location_city': city,
            'min_salary': salary_min,
            'max_salary': salary_max,
        }
        cleaned_jobs.append(job_record)
        
    return pd.DataFrame(cleaned_jobs)