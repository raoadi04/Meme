from typing import Optional

from langchain.embeddings import HuggingFaceEmbeddings

from embedchain.config import BaseEmbedderConfig
from embedchain.embedder.BaseEmbedder import BaseEmbedder
from embedchain.models import EmbeddingFunctions


class HuggingFaceEmbedder(BaseEmbedder):
    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        embeddings = HuggingFaceEmbeddings(model_name=config.model)
        embedding_fn = BaseEmbedder._langchain_default_concept(embeddings)

        vector_dimensions = EmbeddingFunctions.HUGGING_FACE.value

        super().__init__(embedding_fn=embedding_fn, vector_dimensions=vector_dimensions)
