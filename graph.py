from typing import TypedDict, List, Dict, Any
import pandas as pd
from langgraph.graph import StateGraph, END
import utils

# Define the state that flows through the graph
class PipelineState(TypedDict):
    file_path: str               # path to uploaded CSV
    df: pd.DataFrame             # current DataFrame
    issues: Dict[str, Any]       # detected issues (missing columns, nulls, etc.)
    original_issues: Dict[str, Any]
    final_issues: Dict[str, Any]
    mapping: Dict[str, str]      # column mapping from Groq
    actions: List[str]           # healing actions taken
    healed_csv_path: str         # path to the final cleaned CSV
    retry_count: int

# Initialize the graph
workflow = StateGraph(PipelineState)

# Node 1: Load CSV
def load_csv(state: PipelineState):
    df = pd.read_csv(state["file_path"])
    return {"df": df}

# Node 2: Detect all issues
def detect_issues(state: PipelineState):
    df = state["df"]
    issues = {}
    issues["missing_columns"] = utils.detect_missing_columns(df)
    issues["missing_values"] = utils.detect_missing_values(df)
    issues["duplicate_rows"] = utils.detect_duplicate_rows(df)
    issues["invalid_emails"] = utils.detect_invalid_emails(df)
    issues["negative_values"] = utils.detect_negative_values(df)
    return {
        "issues": issues,
        "original_issues": issues.copy()
    }


def validate_again(state: PipelineState):

    df = state["df"]

    issues = {}

    issues["missing_columns"] = utils.detect_missing_columns(df)
    issues["missing_values"] = utils.detect_missing_values(df)
    issues["duplicate_rows"] = utils.detect_duplicate_rows(df)
    issues["invalid_emails"] = utils.detect_invalid_emails(df)
    issues["negative_values"] = utils.detect_negative_values(df)

    return {
        "issues": issues,
        "final_issues": issues
    }

# Node 3: Retrieve rules and generate mapping (if schema mismatch)
def generate_mapping(state: PipelineState):
    df = state["df"]
    issues = state["issues"]

    # If there are missing columns, we need to heal the schema
    if issues.get("missing_columns"):
        actual_cols = list(df.columns)
        retriever = utils.create_retriever()
        mapping = utils.get_schema_mapping_via_groq(actual_cols, retriever)
        return {"mapping": mapping}
    else:
        return {"mapping": {}}

# Node 4: Apply healing and cleaning
def apply_healing(state: PipelineState):

    df = state["df"]
    mapping = state.get("mapping", {})
    retry = state["retry_count"]

    cleaned_df, actions = utils.heal_dataframe(df, mapping)

    # Preserve actions from previous retries
    all_actions = state["actions"] + actions

    cleaned_path = "data/healed_output.csv"
    cleaned_df.to_csv(cleaned_path, index=False)

    return {
        "df": cleaned_df,
        "actions": all_actions,
        "healed_csv_path": cleaned_path,
        "retry_count": retry + 1
    }

# Define the graph structure
workflow.add_node("load_csv", load_csv)
workflow.add_node("detect_issues", detect_issues)
workflow.add_node("generate_mapping", generate_mapping)
workflow.add_node("apply_healing", apply_healing)
workflow.add_node("validate_again",validate_again)

# Set entry point
workflow.set_entry_point("load_csv")

# Add edges: load -> detect -> (if missing columns -> generate_mapping) -> apply
workflow.add_edge("load_csv", "detect_issues")

# Conditional edge: only generate mapping if there are missing columns
def need_mapping(state: PipelineState):
    if state["issues"].get("missing_columns"):
        return "generate_mapping"
    else:
        return "apply_healing"
    

    
def healing_status(state: PipelineState):

    issues = state["issues"]
    retry = state["retry_count"]

    if retry >= 3:
        return "finish"

    # Schema issue -> LLM required
    if issues["missing_columns"]:
        return "mapping"

    # Only data quality issues -> no LLM needed
    if (
        issues["missing_values"]
        or issues["duplicate_rows"] > 0
        or issues["invalid_emails"] > 0
        or issues["negative_values"] > 0
    ):
        return "clean"

    return "finish"

workflow.add_conditional_edges(
    "detect_issues",
    need_mapping,
    {
        "generate_mapping": "generate_mapping",
        "apply_healing": "apply_healing"
    }
)

workflow.add_conditional_edges(

    "validate_again",

    healing_status,

    {
        "mapping": "generate_mapping",
        "clean": "apply_healing",
        "finish": END
    }

)

workflow.add_edge("generate_mapping", "apply_healing")
workflow.add_edge("apply_healing","validate_again")
# workflow.add_edge("apply_healing", END)

# Compile the graph
app = workflow.compile()