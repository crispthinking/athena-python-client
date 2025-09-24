# grpc/aio/_call.pyi

import grpc
from grpc.aio import Metadata

class AioRpcError(grpc.RpcError):
    def __init__(
        self,
        code: grpc.StatusCode,
        details: str | None = ...,
        initial_metadata: Metadata | None = ...,
        trailing_metadata: Metadata | None = ...,
        debug_error_string: str | None = ...,
    ) -> None: ...
