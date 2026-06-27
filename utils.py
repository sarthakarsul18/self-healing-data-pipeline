import os
import re
import pandas as pd
from dotenv import load_dotenv

# LangChain imports
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.chains import RetrievalQA

# Load environment variables
load_dotenv()

# -------------------------------------------------------------------
# Expected schema (can also be parsed from company_rules.txt)
EXPECTED_SCHEMA = ["transaction_id", "customer_email", "purchase_amount", "purchase_date"]

# -------------------------------------------------------------------
# Data quality detection functions
# -------------------------------------------------------------------
def detect_missing_columns(df):
    """Returns list of expected columns not present in the DataFrame."""
    missing = [col for col in EXPECTED_SCHEMA if col not in df.columns]
    return missing

def detect_missing_values(df):
    """Returns columns with null values and their counts."""
    null_counts = df.isnull().sum()
    missing = {col: count for col, count in null_counts.items() if count > 0}
    return missing

def detect_duplicate_rows(df):
    """Returns count of duplicate rows."""
    dup_count = df.duplicated().sum()
    return dup_count

def detect_invalid_emails(df):
    """Checks the 'customer_email' column for invalid emails."""
    if "customer_email" not in df.columns:
        return 0
    email_col = df["customer_email"].astype(str)
    invalid = email_col[~email_col.apply(is_valid_email)].count()
    return invalid

def is_valid_email(email):
    """Simple email validator."""
    if pd.isna(email):
        return False
    return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email))

def detect_negative_values(df):
    """Checks 'purchase_amount' for negative values."""
    if "purchase_amount" not in df.columns:
        return 0
    neg_count = (df["purchase_amount"] < 0).sum()
    return neg_count

# -------------------------------------------------------------------
# RAG setup using company_rules.txt
# -------------------------------------------------------------------
def load_company_rules(path="docs/company_rules.txt"):
    """Load the company rules text file."""
    with open(path, "r") as f:
        return f.read()

def create_retriever():
    """Create a FAISS vector store retriever from the company rules document."""
    rules_text = load_company_rules()
    # Split the document into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)
    chunks = splitter.split_text(rules_text)
    docs = [Document(page_content=chunk) for chunk in chunks]

    # Use a free, local embedding model
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(docs, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    return retriever

# def get_relevant_rules(retriever, query):
#     """Retrieve relevant rule snippets for a given query."""
#     docs = retriever.get_relevant_documents(query)
#     return "\n".join([doc.page_content for doc in docs])

def get_relevant_rules(retriever, query):
    """Retrieve relevant rule snippets for a given query."""
    docs = retriever.invoke(query)
    return "\n".join(doc.page_content for doc in docs)

# -------------------------------------------------------------------
# Groq LLM schema mapping (healing logic)
# -------------------------------------------------------------------
def get_schema_mapping_via_groq(actual_cols, retriever):
    """
    Use RAG + Groq to generate a JSON mapping from actual to expected columns.
    """
    # Retrieve relevant rules about columns
    query = f"Expected columns: {EXPECTED_SCHEMA}. Actual columns: {actual_cols}"
    relevant_rules = get_relevant_rules(retriever, query)

    # Build the prompt
    prompt = f"""
    You are a data engineer. The company rules state:
    {relevant_rules}

    The downstream database strictly requires these columns: {EXPECTED_SCHEMA}.
    The incoming CSV has these columns: {actual_cols}.

    Match the actual columns to the expected columns based on semantic meaning and the rules above.
    Return ONLY a valid JSON object where the keys are the actual column names and the values are the expected column names.
    Do not include any markdown, explanations, or text outside the JSON."""

    # Initialize Groq LLM (choose a fast model, e.g., llama3-8b-8192)
    llm = ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0
    )

    # Get response
    response = llm.invoke(prompt)
    # The response is an AIMessage; extract content and parse JSON
    mapping_json = response.content.strip()
    # Sometimes the LLM returns extra code fences, remove them
    if mapping_json.startswith("```json"):
        mapping_json = mapping_json[7:-3].strip()
    elif mapping_json.startswith("```"):
        mapping_json = mapping_json[3:-3].strip()
    import json
    try:
        mapping = json.loads(mapping_json)
        return mapping
    except Exception as e:
        print(f"Failed to parse mapping: {e}")
        return {}

# -------------------------------------------------------------------
# Healing actions
# -------------------------------------------------------------------
def heal_dataframe(df, mapping):
    """
    Apply column renaming, then clean the data:
    - Remove duplicates
    - Drop rows with missing essential columns (or fill? For simplicity drop)
    - Fix invalid emails (set to NaN or drop)
    - Fix negative purchase_amount (set to 0 or drop)
    Returns cleaned DataFrame and a summary of actions taken.
    """
    actions = []
    # 1. Rename columns using the mapping
    if mapping:
        df = df.rename(columns=mapping)
        actions.append(f"Renamed columns: {mapping}")

    # 2. Drop duplicate rows
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)
    if before != after:
        actions.append(f"Dropped {before - after} duplicate rows")

    # 3. Handle missing values: drop rows with any nulls (simple, can be improved)
    before = len(df)
    df = df.dropna()
    after = len(df)
    if before != after:
        actions.append(f"Dropped {before - after} rows with missing values")

    # 4. Clean customer_email column
    if "customer_email" in df.columns:
        invalid_emails = df[~df["customer_email"].apply(is_valid_email)].index
        df.loc[invalid_emails, "customer_email"] = None
        df = df.dropna(subset=["customer_email"])
        actions.append(f"Removed {len(invalid_emails)} invalid emails")

    # 5. Fix negative purchase_amount: set to 0 or remove
    if "purchase_amount" in df.columns:
        neg_count = (df["purchase_amount"] < 0).sum()
        if neg_count > 0:
            # Option: replace negative with 0
            df.loc[df["purchase_amount"] < 0, "purchase_amount"] = 0
            actions.append(f"Replaced {neg_count} negative purchase amounts with 0")

    return df, actions