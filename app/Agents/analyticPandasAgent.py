from Tools.PythonExec import RCEpythonTool
from AgentSchema.AgentStateV2 import AgentStatev2
from config.BedrockConfig import get_bedrock_llm
from langchain_core.messages import SystemMessage
import logging
import json

logging.basicConfig(
    filename="agent.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
tools = [RCEpythonTool]

llm_with_tools = get_bedrock_llm().bind_tools(tools)
llm_without_tools = get_bedrock_llm()

MAX_TOOL_CALLS = 5


def AnalyticPandasAgent(state: AgentStatev2):

    files_overview = {
        fname: {
            "sheet_names": fdata.get("sheet_names") or list(fdata.get("sheets_peek", {}).keys()),
            "raw_top_rows_per_sheet": fdata.get("sheets_peek", {})
        }
        for fname, fdata in state["files"].items()
    }

    system_msg = SystemMessage(content=f"""You are an iterative data analysis agent.
Available files in the Python `FILES` dictionary: {list(state["files"].keys())}

Raw top rows of each file/sheet (read with header=None, so indices are 0-based):
{json.dumps(files_overview, indent=2)}

WORKFLOW — follow these steps in order:

STEP 1 — DETERMINE THE HEADER ROW:
  Look at `raw_top_rows_per_sheet`. Each inner list is one row (index 0, 1, 2, …).
  Find the row that contains descriptive column names like "Product Name",
  "Task Name", "Date", "Cost", etc.
  IMPORTANT: the row INDEX of the header row is the value for `skiprows`.
  For example, if row index 5 contains ["", "Product ID", "Product Name", …],
  then use skiprows=5. The header row itself becomes the DataFrame column names
  (it is NOT skipped — `skiprows` only skips the rows BEFORE it).

STEP 2 — VERIFY (first tool call):
  Your FIRST call to RCEpythonTool MUST be a diagnostic:
    import pandas as pd
    df = pd.read_excel(FILES['<filename>'], sheet_name='<sheet>', skiprows=<N>)
    print("COLUMNS:", df.columns.tolist())
    print("SHAPE:", df.shape)
    print(df.head(3))
  Check the output: if the columns show data values (like "P101", "Laptop", 50)
  instead of descriptive names, your skiprows is WRONG — you skipped past the
  header. Decrease skiprows by 1 and retry.

STEP 3 — QUERY (next tool call):
  Use the exact column names from step 2 to write your query.
  Always print() the results.

STEP 4 — ANSWER:
  After seeing the printed output, respond to the user with a clear text answer.

RULES:
- If columns look like data values rather than names, decrease skiprows.
- If you get a KeyError, print df.columns.tolist() to see the real column names.
- NEVER resubmit identical code that just failed.""")

    # Count tool responses only since the last HumanMessage (i.e., this turn)
    tool_response_count = 0
    for m in reversed(state["messages"]):
        if hasattr(m, "type") and m.type == "tool":
            tool_response_count += 1
        elif hasattr(m, "type") and m.type == "human":
            break  # stop counting at the most recent user message

    if tool_response_count >= MAX_TOOL_CALLS:
        # Force a final text answer — no tools available
        logging.info(f"Tool call limit reached ({tool_response_count} tool responses). Forcing final answer.")
        force_msg = SystemMessage(content=(
            "You have used all your allowed tool calls. You MUST now give a final "
            "text answer to the user based on everything you have learned so far. "
            "Do NOT call any tools."
        ))
        response = llm_without_tools.invoke([system_msg] + list(state["messages"]) + [force_msg])
    else:
        remaining = MAX_TOOL_CALLS - tool_response_count
        logging.info(f"Tool calls used: {tool_response_count}/{MAX_TOOL_CALLS} (remaining: {remaining})")
        response = llm_with_tools.invoke([system_msg] + list(state["messages"]))

    logging.info("============LLM generation ==================")
    logging.info(response)
    logging.info("============LLM generation Ends ================== ")
    return {"messages": [response]}
