"""中间件管道：按顺序执行 before 钩子，逆序执行 after 钩子。"""
from request import Request, Response
from middleware import Middleware


class Pipeline:
    def __init__(self):
        self._middlewares = []

    def add(self, middleware: Middleware):
        self._middlewares.append(middleware)
        return self

    def execute(self, request: Request, handler) -> Response:
        """
        执行管道：
        1. 正序执行所有 before 钩子
        2. 调用 handler
        3. 逆序执行所有 after 钩子
        """
        # before 钩子
        for mw in self._middlewares:
            request = mw.before(request)

        # 调用处理器
        response = handler(request)

        # after 钩子
        for mw in self._middlewares:
            response = mw.after(request, response)

        return response
