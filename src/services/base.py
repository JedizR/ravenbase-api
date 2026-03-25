from abc import ABC


class BaseService(ABC):  # noqa: B024
    """All services extend this. cleanup() releases resources."""

    def cleanup(self) -> None:  # noqa: B027
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        self.cleanup()
