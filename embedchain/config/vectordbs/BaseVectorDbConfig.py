from typing import Optional

from embedchain.config.BaseConfig import BaseConfig
from embedchain.models.VectorDimensions import VectorDimensions


class BaseVectorDbConfig(BaseConfig):
    def __init__(
        self,
        collection_name: Optional[str] = None,
        dir: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[str] = None,
        vector_dim: Optional[VectorDimensions] = None,
    ):
        self.collection_name = collection_name or "embedchain_store"
        self.dir = dir or "db"
        self.host = host
        self.port = port
        self.vector_dim = vector_dim
