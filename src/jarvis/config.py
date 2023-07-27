import os

from typing import Literal
from pydantic import BaseModel, Field


class LlamaCache(BaseModel):
    enabled: bool = Field(False)
    kind: Literal['ram', 'disk'] = Field('ram')
    size: int = Field(2 << 30)

class Config(BaseModel):
    llama: dict = Field()
    llama_cache: LlamaCache = Field()
    llama_completions: dict = Field()
    embeddings_path: str = Field(os.path.join('data', 'models', 'embeddings', 'e5-large-v2'))
