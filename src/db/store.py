from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from numpy import percentile

from redis.commands.search.field import TextField

from typing import List, Optional
from dataclasses import dataclass

from db.redis import RedisDB
from config import Config, Rag


@dataclass
class Document:
    source: str
    content: str

    @property
    def id(self) -> str:
        return f'ingest:{self.source}'


class Store:
    embed: SentenceTransformer
    rdb: RedisDB
    rag: Rag

    def __init__(self, conf: Config):
        self.embed = SentenceTransformer(
            'data/embeddings/e5-large-v2', device='cuda')
        self.rdb = RedisDB(self.embed)
        self.rdb.ensure_index(
            'ingest',
            TextField(name='source'),
            TextField(name='content'),
        )
        self.rag = conf.rag

    def list(self) -> List[Document]:
        docs = self.rdb.list('ingest', {
            'source': None,
            'content': None,
        })
        return [
            Document(doc.source, doc.content)
            for doc in docs
        ]

    def get(self, source: str) -> Optional[Document]:
        if not (doc := self.rdb.get('ingest', {
            'source': source,
            'content': None,
        })):
            return None
        return Document(doc.source, doc.content)

    def add(self, doc: Document):
        data = {'source': doc.source, 'content': doc.content}
        self.rdb.set(doc.id, data, doc.content)

    def delete(self, doc: Document) -> bool:
        return self.rdb.delete('ingest', doc.id)

    def search(self, text: str, top_k: int = 1) -> List[Document]:
        docs = self.rdb.search('ingest', text, top_k,
                               self.rag.score_threshold, 'source', 'content')
        return [self.condense(text, doc) for doc in docs]

    def condense(self, text: str, doc: Document) -> Document:
        q = [self.embed.encode(text)]
        split = [d for d in doc.content.split('\n\n') if d.strip()]
        embeds = list(map(lambda d: self.embed.encode(
            d, show_progress_bar=False), split))
        cos = cosine_similarity(q, embeds)
        sub = [split[i] for i, score in enumerate(cos[0])
               if score > percentile(cos[0], self.rag.similarity_percentile)]
        return Document(doc.source, '\n---\n'.join(sub))
