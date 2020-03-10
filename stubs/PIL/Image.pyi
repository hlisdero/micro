from typing import BinaryIO, Optional, Tuple

# from .ImageFile import ImageFile

class Image:
    format: Optional[str]
    size: Tuple[int, int]

    def thumbnail(self, size: Tuple[int, int], resample: int = ...) -> None: ...

    def save(self, fp: BinaryIO, format: str = None) -> None: ...

def open(fp: BinaryIO, mode: str = ...) -> Image: ...
