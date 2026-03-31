from abc import ABC, abstractmethod
from typing import Any


class BaseAlgorithm(ABC):
    name = "base"

    @property
    @abstractmethod
    def ready(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def predict(self, image_source: Any) -> list[dict]:
        raise NotImplementedError
