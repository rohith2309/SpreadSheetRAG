from typing import Annotated, Any, Dict, List, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class FileEntry(TypedDict):
    file_id: str
    s3_url: str
    sheet_names: List[str]
    sheets_peek: Dict[str, List[List[str]]]  # {sheet_name: top_8_rows}

class AgentStatev2(TypedDict):
    session: str
    files: Dict[str, FileEntry]  # Keyed by safe_filename
    messages: Annotated[Sequence[BaseMessage], add_messages]