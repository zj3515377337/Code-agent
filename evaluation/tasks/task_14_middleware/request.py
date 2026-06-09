"""HTTP 请求模型。"""


class Request:
    def __init__(self, method: str, path: str, headers: dict = None, body: str = ""):
        self.method = method
        self.path = path
        self.headers = headers or {}
        self.body = body
        self._metadata = {}

    def set_meta(self, key: str, value):
        self._metadata[key] = value

    def get_meta(self, key: str, default=None):
        return self._metadata.get(key, default)


class Response:
    def __init__(self, status: int = 200, body: str = ""):
        self.status = status
        self.body = body
        self.headers = {}

    def set_header(self, key: str, value: str):
        self.headers[key] = value
