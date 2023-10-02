from collections import deque
import discord
import tiktoken

from dataclasses import dataclass
from typing import Deque, List, Dict


@dataclass
class Message:
    role: str
    content: str = ''
    token_len: int = 0


class Exchange:
    user: str
    prompt: str
    assistant: str
    response: str

    def __init__(self, m1: Message, m2: Message):
        self.user = m1.role
        self.prompt = m1.content
        self.assistant = m2.role
        self.response = m2.content


class Conversation:
    bot_id: int
    token_len: int
    curr_len: int
    # Use tiktoken to reduce message passing to Llama.
    # This is just used to count token length, not actually send tokens.
    tokenizer = tiktoken.Encoding
    roles: Dict[str, str]
    history: Deque[Message]

    def __init__(
            self, bot_id: int, messages_len: int, token_len: int,
            roles: Dict[str, str]):
        self.bot_id = bot_id
        self.token_len = token_len
        self.curr_len = 0
        self.tokenizer = tiktoken.encoding_for_model('gpt-3.5-turbo')
        self.roles = roles
        self.history = deque([], messages_len)

    def prepend(self, message: discord.Message) -> bool:
        return self._add(message, True)

    def append(self, message: discord.Message):
        return self._add(message, False)

    def _add(self, message: discord.Message, prepend: bool) -> bool:
        content = message.content
        content_len = len(self.tokenizer.encode(content))
        if prepend:
            if self.curr_len + content_len > self.token_len:
                return False
        else:
            while self.curr_len + content_len > self.token_len:
                oldest = self.history.pop(0)
                self.curr_len -= oldest.token_len

        is_assistant = message.author.id == self.bot_id
        linked = 0 if prepend else -1
        if self.history and self.history[linked].role == self.roles.assistant and is_assistant:
            self.curr_len += content_len
            self.history[linked].content = f'{content}\n' + self.history[linked].content
            self.history[linked].token_len += content_len
        else:
            token_len = content_len
            self.curr_len += token_len
            added = Message(
                role=self.roles.assistant if is_assistant else self.roles.user,
                content=content,
                token_len=token_len
            )
            if prepend:
                self.history.appendleft(added)
            else:
                self.history.append(added)

        return True

    def replay(self) -> List[Message]:
        return list(self.history)
