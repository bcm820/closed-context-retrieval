from llama_cpp import Llama as LlamaCpp
from llama_cpp import LlamaRAMCache, LlamaDiskCache
from dataclasses import dataclass
from typing import Dict, Literal

from jarvis.config import Config


@dataclass
class Message:
    role: Literal['SYSTEM', 'USER', 'ASSISTANT']
    content: str = ''


class Llama:
    llm: LlamaCpp
    conf: Config

    def __init__(self, conf: Config):
        self.conf = conf
        self.llm = LlamaCpp(**conf.llama)
        if conf.llama_cache.enabled:
            if conf.llama_cache.kind == 'ram':
                self.llm.set_cache(LlamaRAMCache(
                    capacity_bytes=conf.llama_cache.size))
            else:
                self.llm.set_cache(LlamaDiskCache(
                    capacity_bytes=conf.llama_cache.size))

    def complete(self, prompt: str, opts: Dict):
        opts = opts | self.conf.llama_completions
        opts['stream'] = True

        completions = self.llm.__call__(prompt, **opts)
        paragraph = ''
        for chunk in completions:
            text = chunk['choices'][0]['text']
            if '\n' in text:
                split = text.split('\n')
                paragraph += split[0]
                yield paragraph
                paragraph = split[1]
                continue
            paragraph += text
        if paragraph.strip() != '':
            yield paragraph
