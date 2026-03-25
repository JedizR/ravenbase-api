from abc import ABC


class BaseAdapter(ABC):  # noqa: B024
    """All adapters extend this. cleanup() closes external connections."""

    def cleanup(self) -> None:  # noqa: B027
        pass
