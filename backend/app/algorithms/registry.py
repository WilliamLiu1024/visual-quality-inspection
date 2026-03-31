from ..config import DETECTOR_NAME
from .yolo26 import Yolo26Algorithm


ALGORITHM_REGISTRY = {
    "yolo26": Yolo26Algorithm,
}


def create_algorithm(name: str | None = None):
    detector_name = (name or DETECTOR_NAME).lower()
    algorithm_cls = ALGORITHM_REGISTRY.get(detector_name)
    if algorithm_cls is None:
        available = ", ".join(sorted(ALGORITHM_REGISTRY))
        raise ValueError(f"未知算法: {detector_name}，可选值: {available}")
    return algorithm_cls()
