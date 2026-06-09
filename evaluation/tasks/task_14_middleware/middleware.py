"""中间件基类和内置中间件。"""
from request import Request, Response


class Middleware:
    def before(self, request: Request) -> Request:
        """请求前置处理，返回修改后的 request。"""
        return request

    def after(self, request: Request, response: Response) -> Response:
        """响应后置处理，返回修改后的 response。"""
        return response


class AuthMiddleware(Middleware):
    """认证中间件：检查 Authorization 头。"""
    def before(self, request: Request) -> Request:
        if request.path.startswith("/admin") and "Authorization" not in request.headers:
            raise PermissionError("Unauthorized")
        return request

    def after(self, request: Request, response: Response) -> Response:
        response.set_header("X-Auth", "checked")
        return response


class LoggingMiddleware(Middleware):
    """日志中间件：记录请求路径。"""
    def __init__(self):
        self.log = []

    def before(self, request: Request) -> Request:
        self.log.append(f"REQ: {request.method} {request.path}")
        return request

    def after(self, request: Request, response: Response) -> Response:
        self.log.append(f"RES: {response.status}")
        return response


class CorsMiddleware(Middleware):
    """CORS 中间件：添加跨域头。"""
    def after(self, request: Request, response: Response) -> Response:
        response.set_header("Access-Control-Allow-Origin", "*")
        return response
