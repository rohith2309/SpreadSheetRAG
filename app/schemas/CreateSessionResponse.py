from pydantic import BaseModel, Field


class CreateSessionResponse(BaseModel):
    session_id: str = Field(..., description="The unique identifier for the created session")
    msg: str = Field(..., description="A message indicating the status of the session creation")