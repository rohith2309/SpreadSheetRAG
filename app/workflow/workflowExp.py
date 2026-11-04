from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode,tools_condition
from AgentSchema.AgentStateV2 import AgentStatev2
from Agents.analyticPandasAgent import AnalyticPandasAgent
from Tools.PythonExec import RCEpythonTool

tool_node = ToolNode([RCEpythonTool])

builder = StateGraph(AgentStatev2)

# 1. Add the Agent node and the prebuilt ToolNode
builder.add_node("agent", AnalyticPandasAgent)
builder.add_node("tools", tool_node)

# 2. Define the execution flow
builder.add_edge(START, "agent")

# 3. Conditional edge:
# - If Bedrock returns a tool_call for `RCEpythonTool`, route to "tools"
# - If Bedrock returns a final text answer, route to END
builder.add_conditional_edges("agent", tools_condition)

# 4. Loop tool output back to the agent so it can read stdout/errors and decide next steps
builder.add_edge("tools", "agent")

# 5. Export the compiled graph for your FastAPI /ws endpoint
expgraph = builder.compile()