from abc import ABC


class BaseAdapter(ABC):
    """All adapters extend this. cleanup() closes external connections."""

    def cleanup(self) -> None:
        pass
