import os
import streamlit as st
from dotenv import load_dotenv
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


# 2. Connect to PostgreSQL
# Remove @st.cache_resource for now to ensure fresh DB reflection
def get_database_connection():
    db_uri = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    # Explicitly include only your exact postgres table
    return SQLDatabase.from_uri(db_uri, include_tables=['uk_job_postings'])

db = get_database_connection()


# 3. Initialize the Groq LLM
llm = ChatGroq(
    temperature=0,
    model_name="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY,
    max_retries=3 # Groq is generous, but it's still good practice to have a small retry buffer
)


# 4. Create the LangChain SQL Agent
# System prompt to guide the AI to write cleaner, more accurate SQL
custom_prefix = """
You are an expert SQL analyst querying the 'uk_job_postings' table.
When filtering by job roles, ALWAYS use the 'role_category' column directly (e.g., role_category = 'Data Engineer') rather than searching job_title unless specifically asked for a custom job title.
Always order salary queries by max_salary DESC.
"""

agent_executor = create_sql_agent(
    llm=llm, 
    db=db, 
    agent_type="tool-calling",
    verbose=True,
    prefix=custom_prefix, # Guide the AI's SQL logic
    agent_executor_kwargs={"handle_parsing_errors": True}
)


# 5. Streamlit Frontend UI
st.set_page_config(page_title="UK Job Market AI", page_icon="🤖")
st.title("🤖 UK Data Job Market Assistant")
st.markdown("Ask me anything about the job market, salaries, or specific roles in the UK!")

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