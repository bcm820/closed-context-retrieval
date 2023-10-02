import sentence_transformers
import numpy as np

from redis.client import Redis
from redis.commands.search.document import Document
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.field import Field, VectorField
from redis.commands.search.query import Query
from redis.commands.search.result import Result

from typing import Dict, List, Any, Optional


class RedisDB:
    rdb: Redis
    embed: sentence_transformers.SentenceTransformer

    def __init__(self, embed: sentence_transformers.SentenceTransformer):
        self.rdb = Redis()
        self.embed = embed

    def ensure_index(self, index_name: str, *fields: Field):
        try:
            print(self.rdb.ft(index_name).info())
        except:
            print(f'Creating {index_name} index')
            fields = (*fields, VectorField(
                name='vec',
                algorithm='HNSW',
                attributes={
                    'TYPE': 'FLOAT32',
                    'DIM': 1024,
                    'DISTANCE_METRIC': 'Cosine'
                },
            ))
            definition = IndexDefinition(
                prefix=[f'{index_name}:'],
                index_type=IndexType.HASH)
            self.rdb.ft(index_name).create_index(
                fields=fields,
                definition=definition,
                skip_initial_scan=True)
            print(self.rdb.ft(index_name).info())
    
    def list(self, index_name: str, fields: Dict[str, Any]) -> List[Document]:
        if not [v for v in list(fields.values()) if v]:
            query = Query('*')
        else:
            query = Query(
                ' '.join([f'@{k}:{v}' for k, v in fields.items() if v]))
        query = query.return_fields(*fields.keys()).dialect(2)
        print(f'redis.list: {query.query_string()}')
        result: Result = self.rdb.ft(index_name).search(query)
        return result.docs

    def get(self, index_name: str, fields: Dict[str, Any]) -> Optional[Document]:
        query = (Query(' '.join([f'@{k}:{v}' for k, v in fields.items() if v]))
                 .return_fields(*fields.keys())
                 .dialect(2))
        print(f'redis.get: {query.query_string()}')
        result: Result = self.rdb.ft(index_name).search(query)
        if not result.docs:
            return None
        return result.docs[0]

    def set(self, name: str, data: Dict[str, Any], content: str):
        print(f'redis.set: {data}')
        vec: np.ndarray = (self.embed
                           .encode(content)
                           .astype(np.float32)
                           .tobytes())
        self.rdb.hset(name=name, mapping=(data | {'vec': vec}))

    def delete(self, index_name: str, name: str) -> bool:
        print(f'redis.delete: {name}')
        return (self.rdb.ft(index_name)
                .delete_document(doc_id=name, delete_actual_document=True)) == 1

    def search(self, index_name: str, content: str, top_k: int, score_threshold: float, *fields: str) -> List[Document]:
        vec: np.ndarray = (self.embed
                           .encode(content)
                           .astype(np.float32)
                           .tobytes())
        query = (Query(f'*=>[KNN {top_k} @vec $vec AS score]')
                 .sort_by('score')
                 .return_fields(*(*fields, 'score'))
                 .dialect(2))
        print(f'redis.search: {query.query_string()}')
        result: Result = self.rdb.ft(index_name).search(query, {'vec': vec})
        return [doc for doc in result.docs if float(doc.score) < score_threshold]
