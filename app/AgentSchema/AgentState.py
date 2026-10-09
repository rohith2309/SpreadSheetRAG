from typing import Annotated, Any, Dict, List, Optional, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class FileMetaData:
    sheetNames : List[str]
    row_count : int
    columns : List[str]
    column_type : Dict[str,str]
    preview :  List[Dict[str,Any]]


class AgentState(TypedDict):
    
    session: str
    
    file_id :str
    file_name: str
    file_url: str  # currently just one file
    
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    meta_data: FileMetaData
    
    generated_code: Optional[str]   
    execution_result: Optional[str] 
    execution_error: Optional[str]  
    retry_count: int              
    
    
    