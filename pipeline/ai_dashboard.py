import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_groq import ChatGroq

# 1. Load Secrets
load_dotenv()
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'job_market_db')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
# NEON_DATABASE_URL takes priority so the dashboard reads the same cloud DB
# the weekly GitHub Actions pipeline writes to; falls back to local Postgres
# (the DB_* vars above) when it isn't set.
DB_URI = os.getenv('NEON_DATABASE_URL') or f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- Palette (validated categorical order — role_category keeps the same
# color in every chart it appears in; see the dataviz skill's palette.md) ---
SURFACE = "#e9e7e0"
PAGE_PLANE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_MUTED = "#898781"
GRIDLINE = "#d6d4cb"
BLUE = "#2a78d6"

ROLE_ORDER = ["Data Engineer", "Data Analyst", "Data Scientist", "BI Developer", "Data Management/Other", "ML Engineer"]
ROLE_COLORS = {
    "Data Engineer": "#2a78d6",
    "Data Analyst": "#eb6834",
    "Data Scientist": "#1baf7a",
    "BI Developer": "#eda100",
    "Data Management/Other": "#e87ba4",
    "ML Engineer": "#4a3aa7",
}
WORK_MODEL_ORDER = ["Onsite", "Hybrid", "Remote"]
WORK_MODEL_COLORS = {"Onsite": "#2a78d6", "Hybrid": "#eb6834", "Remote": "#1baf7a"}


# 2. Connect to PostgreSQL (cached — avoids reconnecting on every rerun)
# The chat agent is pointed at uk_job_postings_chat, a view that excludes
# job_link — Adzuna's job_link is a short-lived tracking redirect that 404s
# within days, so it can never be a reliable answer; excluding the column
# structurally means the agent can't surface it even if asked, rather than
# relying on a prompt instruction it could ignore.
@st.cache_resource
def get_database_connection():
    return SQLDatabase.from_uri(DB_URI, include_tables=['uk_job_postings_chat'], view_support=True)


@st.cache_resource
def get_llm():
    return ChatGroq(
        temperature=0,
        model_name="openai/gpt-oss-120b",
        api_key=GROQ_API_KEY,
        max_retries=3,  # Groq is generous, but it's still good practice to have a small retry buffer
    )


@st.cache_resource
def get_agent_executor():
    custom_prefix = """
You are an expert SQL analyst querying the 'uk_job_postings_chat' view.
When filtering by job roles, ALWAYS use the 'role_category' column directly (e.g., role_category = 'Data Engineer') rather than searching job_title unless specifically asked for a custom job title.
Always order salary queries by max_salary DESC.
This view has no job link/URL column. If asked for a link to apply, explain
that direct links aren't available and suggest searching the job title and
company name on a job board instead.
"""
    return create_sql_agent(
        llm=get_llm(),
        db=get_database_connection(),
        agent_type="tool-calling",
        verbose=True,
        prefix=custom_prefix,
        agent_executor_kwargs={"handle_parsing_errors": True},
    )


@st.cache_data(ttl=600)
def load_jobs_df():
    engine = create_engine(DB_URI)
    return pd.read_sql("SELECT * FROM uk_job_postings", engine)


# 3. Chart helpers
def _style(fig, title, height=340):
    fig.update_layout(
        title=dict(text=title, font=dict(color=INK_PRIMARY, size=16), x=0),
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK_MUTED),
        margin=dict(l=10, r=10, t=48, b=10),
        height=height,
        showlegend=False,
        hoverlabel=dict(bgcolor=SURFACE, font_color=INK_PRIMARY, bordercolor=GRIDLINE),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRIDLINE, tickfont=dict(color=INK_MUTED))
    fig.update_yaxes(showgrid=True, gridcolor=GRIDLINE, linecolor=GRIDLINE, tickfont=dict(color=INK_MUTED))
    return fig


def chart_role_counts(df):
    counts = df['role_category'].value_counts()
    counts = counts.reindex([r for r in ROLE_ORDER if r in counts.index])
    fig = go.Figure(go.Bar(
        x=counts.index, y=counts.values,
        marker_color=[ROLE_COLORS.get(r, INK_MUTED) for r in counts.index],
        hovertemplate="%{x}: %{y} postings<extra></extra>",
    ))
    return _style(fig, "Postings by role category")


def chart_avg_salary_by_role(df):
    avg = df.dropna(subset=['max_salary']).groupby('role_category')['max_salary'].mean()
    avg = avg.reindex([r for r in ROLE_ORDER if r in avg.index]).dropna()
    fig = go.Figure(go.Bar(
        x=avg.index, y=avg.values,
        marker_color=[ROLE_COLORS.get(r, INK_MUTED) for r in avg.index],
        hovertemplate="%{x}: £%{y:,.0f}<extra></extra>",
    ))
    fig.update_yaxes(tickprefix="£", tickformat=",.0f")
    return _style(fig, "Average max salary by role category")


def chart_work_model(df):
    counts = df['work_model'].value_counts()
    counts = counts.reindex([w for w in WORK_MODEL_ORDER if w in counts.index])
    fig = go.Figure(go.Bar(
        x=counts.index, y=counts.values,
        marker_color=[WORK_MODEL_COLORS.get(w, INK_MUTED) for w in counts.index],
        hovertemplate="%{x}: %{y} postings<extra></extra>",
    ))
    return _style(fig, "Postings by work model", height=300)


def chart_top_n(df, column, title, n=8):
    counts = df[column].value_counts().head(n).iloc[::-1]
    fig = go.Figure(go.Bar(
        x=counts.values, y=counts.index, orientation='h',
        marker_color=BLUE,
        hovertemplate="%{y}: %{x} postings<extra></extra>",
    ))
    return _style(fig, title, height=340)


# 4. Streamlit Frontend UI
st.set_page_config(page_title="UK Job Market AI", page_icon="🤖", layout="wide")

# The top nav (st.navigation position="top") renders small by default — size
# it up so a visitor notices there's a second tab, not just cosmetic.
st.markdown(
    """
    <style>
    div[data-testid="stTopNavSection"] {
        gap: 0.5rem;
        padding: 0.4rem 0;
    }
    a[data-testid="stTopNavLink"] {
        font-size: 1.15rem;
        padding: 0.65rem 1.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_header():
    st.title("🤖 UK Data Job Market Assistant")
    st.markdown(
        "Tracking data-related job postings across the UK — sourced from Adzuna, "
        "refreshed automatically every week. Browse the market overview or ask "
        "the AI assistant a question in plain English."
    )


def overview_page():
    render_header()
    df = load_jobs_df()

    if st.button("🔄 Refresh data"):
        load_jobs_df.clear()
        st.rerun()

    total_postings = len(df)
    avg_max_salary = df['max_salary'].mean()
    pct_remote = (df['work_model'] == 'Remote').mean() * 100
    top_role = df['role_category'].value_counts().idxmax() if total_postings else "N/A"

    with st.container(border=True):
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Postings", f"{total_postings:,}")
        k2.metric("Avg Max Salary", f"£{avg_max_salary:,.0f}" if pd.notna(avg_max_salary) else "N/A")
        k3.metric("% Remote", f"{pct_remote:.1f}%")
        k4.metric("Top Role Category", top_role)

    st.subheader("Roles & Salaries")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(chart_role_counts(df), use_container_width=True)
        with c2:
            st.plotly_chart(chart_avg_salary_by_role(df), use_container_width=True)

    st.subheader("Work Model")
    with st.container(border=True):
        st.plotly_chart(chart_work_model(df), use_container_width=True)

    st.subheader("Geography & Employers")
    with st.container(border=True):
        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(chart_top_n(df, 'location_city', "Top cities by postings"), use_container_width=True)
        with c4:
            st.plotly_chart(chart_top_n(df, 'company_name', "Top companies by postings"), use_container_width=True)


def chat_page():
    render_header()
    st.markdown("Ask me anything about the job market, salaries, or specific roles in the UK!")

    agent_executor = get_agent_executor()

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("E.g., What is the highest paying remote Data Engineer role?"):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Searching the database..."):
                try:
                    # The agent automatically writes SQL, runs it, and returns a natural answer
                    response = agent_executor.run(prompt)
                    st.markdown(response)
                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


nav = st.navigation(
    [
        st.Page(overview_page, title="Market Overview", icon="📊"),
        st.Page(chat_page, title="Ask the AI", icon="💬"),
    ],
    position="top",
)
nav.run()
