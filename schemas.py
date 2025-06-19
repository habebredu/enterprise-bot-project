from typing import Optional

from pydantic import BaseModel, Field


class AnswerStructure(BaseModel):
    answer: str = Field(description="The answer to the user's question")
    send: bool = Field(description="Should the question be sent to a human colleague? (True/False)")


class EmailInput(BaseModel):
    email: str


class AskRequest(BaseModel):
    ticket_name: Optional[str] = None
    question: str
