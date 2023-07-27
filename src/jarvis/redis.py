import numpy as np
import sentence_transformers

from redis.client import Redis
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.field import VectorField, TextField
from redis.commands.search.query import Query
from redis.commands.search.result import Result

from typing import List, Union
from dataclasses import dataclass, asdict

from jarvis.config import Config


@dataclass
class ConversationRef:
    guild: str
    channel: str
    message: str
    start: str
    end: str
    summary: str = ''

    def id(self) -> str:
        return f'discord:{self.guild}:{self.channel}:{self.message}'


class RedisDB:
    rdb: Redis
    embed: sentence_transformers.SentenceTransformer

    def __init__(self, conf: Config):
        self.rdb = Redis()
        try:
            self.rdb.ft('discord').info()
        except:
            print('Creating index')
            schema = [
                TextField(name='guild'),
                TextField(name='channel'),
                TextField(name='message'),
                TextField(name='start'),
                TextField(name='end'),
                TextField(name='summary'),
                VectorField(
                    name='vec',
                    algorithm='HNSW',
                    attributes={
                        'TYPE': 'FLOAT32',
                        'DIM': 1024,
                        'DISTANCE_METRIC': 'Cosine'
                    },
                )
            ]
            definition = IndexDefinition(
                prefix=['discord:'],
                index_type=IndexType.HASH)
            self.rdb.ft('discord').create_index(
                fields=schema,
                definition=definition,
                skip_initial_scan=True)

        self.embed = sentence_transformers.SentenceTransformer(
            conf.embeddings_path,
            device='cpu')

    def list(self, guild: int, channel: int) -> List[ConversationRef]:
        query = (Query(f'@guild:{guild} @channel:{channel}')
                 .return_fields('guild', 'channel', 'message', 'start', 'end', 'summary')
                 .dialect(2))
        result: Result = self.rdb.ft('discord').search(query)
        return [
            ConversationRef(guild=result.guild,
                            channel=result.channel,
                            message=result.message,
                            start=result.start,
                            end=result.end,
                            summary=result.summary)
            for result in result.docs
        ]

    def get(self, guild: int, channel: int, message: int) -> Union[ConversationRef, None]:
        query = (Query(f'@guild:{guild} @channel:{channel} @message:{message}')
                 .return_fields('guild', 'channel', 'message', 'start', 'end', 'summary')
                 .dialect(2))
        result: Result = self.rdb.ft('discord').search(query)
        if len(result.docs) == 0:
            return None
        return ConversationRef(guild=result.docs[0].guild,
                               channel=result.docs[0].channel,
                               message=result.docs[0].message,
                               start=result.docs[0].start,
                               end=result.docs[0].end,
                               summary=result.docs[0].summary)

    def set(self, doc: ConversationRef):
        vec: np.ndarray = (self.embed
                           .encode(doc.summary)
                           .astype(np.float32)
                           .tobytes())
        self.rdb.hset(name=doc.id(),
                      mapping=(asdict(doc) | {'vec': vec}))

    def delete(self, guild: int, channel: int, message: int) -> bool:
        id = f'discord:{guild}:{channel}:{message}'
        return (self.rdb.ft('discord')
                .delete_document(doc_id=id, delete_actual_document=True)) == 1

    def search(self, content: str, top_k: int) -> List[ConversationRef]:
        vec: np.ndarray = (self.embed
                           .encode(content)
                           .astype(np.float32)
                           .tobytes())
        query = (Query(f'*=>[KNN {top_k} @vec $vec AS score]')
                 .sort_by('score')
                 .paging(0, 5)
                 .return_fields('guild', 'channel', 'message', 'start', 'end', 'summary', 'score')
                 .dialect(2))
        result: Result = (self.rdb.ft('discord')
                          .search(query, {'vec': vec}))
        return [
            ConversationRef(guild=result.guild,
                            channel=result.channel,
                            message=result.message,
                            start=result.start,
                            end=result.end,
                            summary=result.summary)
            for result in result.docs
            if float(result.score) < 0.2
        ]
