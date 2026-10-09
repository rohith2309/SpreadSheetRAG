from Tools.PythonExec import RCEpythonTool
from AgentSchema.AgentState import AgentState
from config.BedrockConfig import get_bedrock_llm


tools=[RCEpythonTool]

def PandasAgent(state: AgentState):
    
    llm_with_tool = get_bedrock_llm().bind_tools(tools)
    response = llm_with_tool.invoke(
        state["messages"]
    )

    return {
        "messages": [response]
    }