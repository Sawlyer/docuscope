from functools import cached_property

from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType

from .config import settings


class EmbeddingService:
    def __init__(self, model=None):
        self._provided_model = model

    @cached_property
    def model(self):
        if self._provided_model is not None:
            return self._provided_model
        supported = {entry["model"] for entry in TextEmbedding.list_supported_models()}
        if settings.embedding_model not in supported and settings.embedding_model == "intfloat/multilingual-e5-small":
            TextEmbedding.add_custom_model(
                model=settings.embedding_model,
                pooling=PoolingType.MEAN,
                normalization=True,
                sources=ModelSource(hf=settings.embedding_model),
                dim=384,
                model_file="onnx/model.onnx",
            )
        return TextEmbedding(model_name=settings.embedding_model, cache_dir=settings.embedding_cache_dir)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in self.model.embed([f"passage: {text}" for text in texts])]

    def embed_query(self, text: str) -> list[float]:
        vector = next(iter(self.model.embed([f"query: {text}"])))
        return vector.tolist() if hasattr(vector, "tolist") else list(vector)


embedding_service = EmbeddingService()
