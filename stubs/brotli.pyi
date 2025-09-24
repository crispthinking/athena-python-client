# brotli.pyi -- since brotli isn't typed :( thanks, google

# Define the BrotliError exception
class BrotliError(Exception): ...

def compress(
    string: bytes,
    *,
    mode: int = ...,
    quality: int = ...,
    lgwin: int = ...,
    lgblock: int = ...,
    dictionary: bytes = ...,
) -> bytes: ...
def decompress(string: bytes, *, dictionary: bytes = ...) -> bytes: ...
