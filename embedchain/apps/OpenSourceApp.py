import logging
from typing import Optional

from embedchain.config import (BaseEmbedderConfig, ChatConfig, ChromaDbConfig,
                               OpenSourceAppConfig)
from embedchain.embedchain import EmbedChain
from embedchain.embedder.gpt4all_embedder import GPT4AllEmbedder
from embedchain.llm.gpt4all_llm import GPT4ALLLlm
from embedchain.vectordb.chroma_db import ChromaDB

gpt4all_model = None


class OpenSourceApp(EmbedChain):
    """
    The OpenSource app.
    Same as App, but uses an open source embedding model and LLM.

    Has two function: add and query.

    adds(data_type, url): adds the data from the given URL to the vector db.
    query(query): finds answer to the given query using vector database and LLM.
    """

    def __init__(self, config: OpenSourceAppConfig = None, chromadb_config: Optional[ChromaDbConfig] = None):
        """
        :param config: OpenSourceAppConfig instance to load as configuration. Optional.
        `ef` defaults to open source.
        """
        logging.info("Loading open source embedding model. This may take some time...")  # noqa:E501
        if not config:
            config = OpenSourceAppConfig()

        if not config.model:
            raise ValueError("OpenSourceApp needs a model to be instantiated. Maybe you passed the wrong config type?")

        logging.info("Successfully loaded open source embedding model.")

        llm = GPT4ALLLlm(config=ChatConfig(model="orca-mini-3b.ggmlv3.q4_0.bin"))
        embedder = GPT4AllEmbedder(config=BaseEmbedderConfig(model="all-MiniLM-L6-v2"))
        database = ChromaDB(config=chromadb_config, embedder=embedder)

        super().__init__(config, llm=llm, db=database, embedder=embedder)
