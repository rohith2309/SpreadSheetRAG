from pydantic import BaseModel, Field

class CodeSnippet(BaseModel):
    code: str = Field(..., description="The actual code snippet")