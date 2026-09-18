from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="The unique identifier for the session")
    message: str = Field(..., description="The user's message")