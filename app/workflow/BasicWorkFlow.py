from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode,tools_condition
from AgentSchema.AgentState import AgentState
from Agents.pandasAgent import PandasAgent
from Tools.PythonExec import RCEpythonTool

tool_node = ToolNode([RCEpythonTool])


workflow = StateGraph(AgentState)

workflow.add_node("pandas_agent", PandasAgent)
workflow.add_node("tools",tool_node)

workflow.add_edge(START,"pandas_agent")
workflow.add_conditional_edges("pandas_agent", tools_condition)
workflow.add_edge("tools","pandas_agent")

graph = workflow.compile()
