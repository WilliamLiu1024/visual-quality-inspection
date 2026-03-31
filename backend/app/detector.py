from .algorithms import create_algorithm


class DetectorService:
    def __init__(self):
        self.algorithm = create_algorithm()

    @property
    def ready(self) -> bool:
        return self.algorithm.ready

    @property
    def name(self) -> str:
        return self.algorithm.name

    def predict(self, image_source) -> list[dict]:
        return self.algorithm.predict(image_source)
