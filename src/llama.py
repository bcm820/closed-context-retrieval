import sseclient
import requests
import json

from multiprocessing.connection import Connection
from typing import Dict, Any

from config import Config


class Llama:
    conf: Config

    def __init__(self, conf: Config, llm_recv: Connection, bot_send: Connection):
        self.conf = conf
        self.listen(llm_recv, bot_send)

    def create_completion(self, **kwargs):
        response = requests.post(
            url='http://localhost:8080/completion',
            json=kwargs,
            stream=True,
            headers={'Accept': 'text/event-stream'})
        client = sseclient.SSEClient(response)
        return client.events()

    def complete(self, prompt: str, completion_opts: Dict[str, Any]):
        completion_opts = completion_opts | self.conf.completions
        if not 'stop' in completion_opts:
            completion_opts['stop'] = []
        completion_opts['stop'] += [
            f'{self.conf.roles.user}'.rstrip(),
            f'{self.conf.roles.assistant}'.rstrip(),
        ]
        completion_opts['stream'] = True
        completion_opts['prompt'] = prompt

        def gen_lines():
            line = ''
            for event in self.create_completion(**completion_opts):
                chunk = json.loads(event.data)
                if chunk['stop']:
                    break
                text = chunk['content']
                if '\n' in text:
                    split = text.split('\n')
                    line += split[0]
                    if line:
                        yield f'{line}\n'
                    line = split[1]
                    continue
                line += text
            if line.strip():
                yield f'{line}\n'

        code_block = ''
        language = ''
        for line in gen_lines():
            if line.startswith('```'):
                # Code blocks are sent in a single message
                # If code_block is empty, start the code block with this line
                if not code_block:
                    language = line.lstrip()[3:].strip()
                    code_block = line
                # This is the end of the code block; send it and empty it
                else:
                    yield code_block + line
                    code_block = ''
            # If we're not in a code block, send the line by itself
            # This assumes lines won't ever reach Discord's 2k character limit
            elif not code_block:
                yield line
            # If we're in a code block and still under the char limit, extend it
            elif len(code_block) + len(line) <= 1900:
                code_block += line
            # The code block is too long; split it into two functional code blocks
            else:
                yield code_block + '```\n'
                code_block = f'```{language}\n{line}'

    def listen(self, llm_recv: Connection, bot_send: Connection):
        while True:
            llm_recv.poll(timeout=None)
            prompt, opts = llm_recv.recv()
            print(f'\n{prompt}')
            for line in self.complete(prompt, opts):
                bot_send.send(line)
            bot_send.send('EOF')
