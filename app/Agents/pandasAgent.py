from Tools.PythonExec import RCEpythonTool
from AgentSchema.AgentState import AgentState
from config.BedrockConfig import get_bedrock_llm
from langchain_core.messages import SystemMessage
import logging

logging.basicConfig(
    filename="agent.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
tools=[RCEpythonTool]

# def PandasAgent(state: AgentState):
    
#     llm_with_tool = get_bedrock_llm().bind_tools(tools)
#     response = llm_with_tool.invoke(
#         state["messages"]
#     )

#     return {
#         "messages": [response]
#     }

def PandasAgent(state: AgentState):

    metadata = state["meta_data"]
    logging.info(
    "NODE META=%s",
    state.get("meta_data")
        )

    system_prompt = system_prompt = SystemMessage(
    content=f"""
    You are a data analysis agent.

    Dataset Information:

    Columns:
    {metadata["columns"]}

    Column Types:
    {metadata["column_type"]}

    Sample Rows:
    {metadata["preview"]}

    Known Values:
    {metadata["unique_vals"]}

    Rules:
    1. Never invent column names.
    2. Use only the provided schema.
    3. If a business term is mentioned, determine whether it is:
        - a column name
        - or a value within a column
    4. Prefer exact filtering using values from Known Values.
    5. Use text search on Description only when the concept is not present in Known Values.
    6. Generate Python pandas code when analysis is required.
    """
   )

    messages = [
        system_prompt,
        *state["messages"]
    ]

    response = (
        get_bedrock_llm()
        .bind_tools(tools)
        .invoke(messages)
    )

    return {
        "messages": [response]
    }