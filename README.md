# UK Data Job Market Analytics

**Live dashboard:** [job-market-analytics-dash-j7e9sixyphp7wbvnappqpei.streamlit.app](https://job-market-analytics-dash-j7e9sixyphp7wbvnappqpei.streamlit.app/)

An end-to-end data platform that tracks data-related job postings across the UK. A weekly pipeline pulls listings from the Adzuna API, cleans and categorizes them, and loads new postings into a Postgres (Neon) database. A Streamlit dashboard sits on top, offering a market overview with KPIs and charts plus an AI chat assistant that answers plain-English questions about the data by writing SQL under the hood.

## Features

- **Automated weekly ETL** — a GitHub Actions workflow extracts, transforms, and loads new UK data job postings every Monday, deduplicating against what's already in the database.
- **Market overview dashboard** — KPI tiles (total postings, average salary, % remote, top role) and charts for role distribution, salary by role, work model, top cities, and top companies.
- **AI chat assistant** — ask questions like *"What is the highest paying remote Data Engineer role?"* and get answers from a LangChain SQL agent (Groq-hosted LLM) querying the live database.
- **Role categorization** — postings are automatically bucketed into Data Analyst, Data Engineer, Data Scientist, ML Engineer, BI Developer, or Data Management/Other based on title and description.
- **Work model detection** — Remote / Hybrid / Onsite inferred from title, description, and location text.

## Architecture

```
Adzuna API → extract_jobs.py → transform_jobs.py → load_jobs.py → Postgres (Neon)
                                                                        │
                                                                        ▼
                                                          ai_dashboard.py (Streamlit)
                                                          ├─ Market Overview (Plotly)
                                                          └─ AI Chat (LangChain + Groq)
```

- `pipeline/extract_jobs.py` — paginates through the Adzuna API for UK "data" job listings.
- `pipeline/transform_jobs.py` — filters noise, categorizes roles, extracts salary/location/work-model fields.
- `pipeline/load_jobs.py` — loads new rows into `uk_job_postings`, deduplicating on `job_link`.
- `pipeline/ai_dashboard.py` — the Streamlit app (Market Overview + Ask the AI tabs).
- `.github/workflows/weekly_pipeline.yml` — runs the extract → load steps on a weekly schedule against the Neon database.

## Getting started

### Prerequisites

- Python 3.12+
- A Postgres database (local or [Neon](https://neon.tech))
- An [Adzuna API](https://developer.adzuna.com/) app ID/key
- A [Groq API](https://console.groq.com/) key (powers the AI chat assistant)

### Setup

1. Clone the repo and install dependencies:

   ```bash
   pip install -r pipeline/requirements.txt
   ```

2. Create a `.env` file in the project root with:

   ```
   ADZUNA_APP_ID=your_app_id
   ADZUNA_APP_KEY=your_app_key

   # Local Postgres (used if NEON_DATABASE_URL / DATABASE_URL isn't set)
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_NAME=job_market_db

   GROQ_API_KEY=your_groq_key
   NEON_DATABASE_URL=your_neon_connection_string
   ```

3. Run the pipeline to populate the database:

   ```bash
   cd pipeline
   python extract_jobs.py
   python load_jobs.py
   ```

4. Launch the dashboard:

   ```bash
   streamlit run pipeline/ai_dashboard.py
   ```

### Automated weekly refresh

`.github/workflows/weekly_pipeline.yml` runs every Monday (and can be triggered manually from the Actions tab). It expects these repository secrets:

- `ADZUNA_APP_ID`
- `ADZUNA_APP_KEY`
- `NEON_DATABASE_URL`

## Tech stack

- **Data**: Adzuna API, pandas
- **Database**: PostgreSQL (Neon), SQLAlchemy
- **Dashboard**: Streamlit, Plotly
- **AI**: LangChain SQL agent, Groq (`openai/gpt-oss-120b`)
- **Automation**: GitHub Actions
