from typing import Any, Dict, List

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import bulk
except ImportError:
    raise ImportError(
        "Elasticsearch requires extra dependencies. Install with `pip install embedchain[elasticsearch]`"
    ) from None

from embedchain.config import ElasticsearchDBConfig
from embedchain.helper_classes.json_serializable import register_deserializable
from embedchain.vectordb.base_vector_db import BaseVectorDB


@register_deserializable
class ElasticsearchDB(BaseVectorDB):
    def __init__(
        self,
        config: ElasticsearchDBConfig = None,
        es_config: ElasticsearchDBConfig = None,  # Backwards compatibility
    ):
        """
        Elasticsearch as vector database
        :param es_config. elasticsearch database config to be used for connection
        :param embedding_fn: Function to generate embedding vectors.
        :param vector_dim: Vector dimension generated by embedding fn
        """
        if config is None and es_config is None:
            raise ValueError("ElasticsearchDBConfig is required")
        self.config = config or es_config
        self.client = Elasticsearch(es_config.ES_URL, **es_config.ES_EXTRA_PARAMS)

        # Call parent init here because embedder is needed
        super().__init__(config=self.config)

    def _initialize(self):
        """
        This method is needed because `embedder` attribute needs to be set externally before it can be initialized.
        """
        index_settings = {
            "mappings": {
                "properties": {
                    "text": {"type": "text"},
                    "embeddings": {"type": "dense_vector", "index": False, "dims": self.embedder.vector_dimension},
                }
            }
        }
        es_index = self._get_index()
        if not self.client.indices.exists(index=es_index):
            # create index if not exist
            print("Creating index", es_index, index_settings)
            self.client.indices.create(index=es_index, body=index_settings)

    def _get_or_create_db(self):
        return self.client

    def _get_or_create_collection(self, name):
        """Note: nothing to return here. Discuss later"""

    def get(self, ids: List[str], where: Dict[str, any]) -> List[str]:
        """
        Get existing doc ids present in vector database
        :param ids: list of doc ids to check for existance
        :param where: Optional. to filter data
        """
        query = {"bool": {"must": [{"ids": {"values": ids}}]}}
        if "app_id" in where:
            app_id = where["app_id"]
            query["bool"]["must"].append({"term": {"metadata.app_id": app_id}})
        response = self.client.search(index=self.es_index, query=query, _source=False)
        docs = response["hits"]["hits"]
        ids = [doc["_id"] for doc in docs]
        return set(ids)

    def add(self, documents: List[str], metadatas: List[object], ids: List[str]) -> Any:
        """
        add data in vector database
        :param documents: list of texts to add
        :param metadatas: list of metadata associated with docs
        :param ids: ids of docs
        """
        docs = []
        embeddings = self.embedder.embedding_fn(documents)
        for id, text, metadata, embeddings in zip(ids, documents, metadatas, embeddings):
            docs.append(
                {
                    "_index": self._get_index(),
                    "_id": id,
                    "_source": {"text": text, "metadata": metadata, "embeddings": embeddings},
                }
            )
        bulk(self.client, docs)
        self.client.indices.refresh(index=self._get_index())
        return

    def query(self, input_query: List[str], n_results: int, where: Dict[str, any]) -> List[str]:
        """
        query contents from vector data base based on vector similarity
        :param input_query: list of query string
        :param n_results: no of similar documents to fetch from database
        :param where: Optional. to filter data
        """
        input_query_vector = self.embedder.embedding_fn(input_query)
        query_vector = input_query_vector[0]
        query = {
            "script_score": {
                "query": {"bool": {"must": [{"exists": {"field": "text"}}]}},
                "script": {
                    "source": "cosineSimilarity(params.input_query_vector, 'embeddings') + 1.0",
                    "params": {"input_query_vector": query_vector},
                },
            }
        }
        if "app_id" in where:
            app_id = where["app_id"]
            query["script_score"]["query"]["bool"]["must"] = [{"term": {"metadata.app_id": app_id}}]
        _source = ["text"]
        response = self.client.search(index=self._get_index(), query=query, _source=_source, size=n_results)
        docs = response["hits"]["hits"]
        contents = [doc["_source"]["text"] for doc in docs]
        return contents

    def set_collection_name(self, name: str):
        self.config.collection_name = name

    def count(self) -> int:
        query = {"match_all": {}}
        response = self.client.count(index=self._get_index(), query=query)
        doc_count = response["count"]
        return doc_count

    def reset(self):
        # Delete all data from the database
        if self.client.indices.exists(index=self._get_index()):
            # delete index in Es
            self.client.indices.delete(index=self._get_index())

    def _get_index(self):
        # NOTE: The method is preferred to an attribute, because if collection name changes,
        # it's always up-to-date.
        return f"{self.config.collection_name}_{self.embedder.vector_dimension}"
