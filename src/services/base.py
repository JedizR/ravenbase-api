from abc import ABC


class BaseService(ABC):
    """All services extend this. cleanup() releases resources."""

    def cleanup(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        self.cleanup()
