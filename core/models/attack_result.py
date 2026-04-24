from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PromptResult(BaseModel):
    prompt: str
    response: str
    passed: bool
    score: Optional[float] = None
    rationale: Optional[str] = None
    detector: Optional[str] = None # Pour garak only


class ConversationTurn(BaseModel):
    turn: int
    prompt: str
    response: str
    score: bool
    rationale: Optional[str] = None


class Conversation(BaseModel):
    conversation_id : str
    objective: str
    achieved: bool
    turns: list[ConversationTurn]



class AttackResult(BaseModel):
    framework: str
    attack_name: str
    target_url: str
    timestamp: datetime = datetime.now()

    # garak — flat list of independent prompts
    prompts: Optional[list[PromptResult]] = None

    # pyrit — one single conversation
    conversation: Optional[Conversation] = None

    def save(self, path: str):
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=2))
