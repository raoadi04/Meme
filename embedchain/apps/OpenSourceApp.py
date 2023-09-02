import logging
from typing import Iterable, Optional, Union

from chromadb.utils import embedding_functions

from embedchain.config import ChatConfig, ChromaDbConfig, OpenSourceAppConfig
from embedchain.config.embedder.embedder_config import EmbedderConfig
from embedchain.embedchain import EmbedChain
from embedchain.embedder.embedder import Embedder
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

        self.instance = OpenSourceApp._get_instance(config.model)

        logging.info("Successfully loaded open source embedding model.")

        database = ChromaDB(config=chromadb_config)
        embedder = Embedder(config=EmbedderConfig(embedding_fn=OpenSourceApp.default_embedding_function()))

        super().__init__(config, db=database, embedder=embedder)

    def get_llm_model_answer(self, prompt, config: ChatConfig):
        return self._get_gpt4all_answer(prompt=prompt, config=config)

    @staticmethod
    def _get_instance(model):
        try:
            from gpt4all import GPT4All
        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "The GPT4All python package is not installed. Please install it with `pip install embedchain[opensource]`"  # noqa E501
            ) from None

        return GPT4All(model)

    def _get_gpt4all_answer(self, prompt: str, config: ChatConfig) -> Union[str, Iterable]:
        if config.model and config.model != self.config.model:
            raise RuntimeError(
                "OpenSourceApp does not support switching models at runtime. Please create a new app instance."
            )

        if config.system_prompt:
            raise ValueError("OpenSourceApp does not support `system_prompt`")

        response = self.instance.generate(
            prompt=prompt,
            streaming=config.stream,
            top_p=config.top_p,
            max_tokens=config.max_tokens,
            temp=config.temperature,
        )
        return response

    @staticmethod
    def default_embedding_function():
        """
        Sets embedding function to default (`all-MiniLM-L6-v2`).

        :returns: The default embedding function
        """
        try:
            return embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        except ValueError as e:
            print(e)
            raise ModuleNotFoundError(
                "The open source app requires extra dependencies. Install with `pip install embedchain[opensource]`"
            ) from None
