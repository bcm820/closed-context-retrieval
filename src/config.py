from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Rag:
    score_threshold: float
    similarity_percentile: int


@dataclass
class Roles:
    user: str
    assistant: str


@dataclass
class Template:
    system: str
    body: str
    prompt: str


class Config:
    completions: Dict[str, Any]
    rag: Rag
    roles: Roles
    template: Template

    def __init__(self,
                 completions: Dict[str, Any],
                 rag: Dict[str, Any],
                 roles: Dict[str, str],
                 template: Dict[str, str]):
        self.completions = completions
        self.rag = Rag(**rag)
        self.roles = Roles(**roles)
        self.template = Template(**template)
