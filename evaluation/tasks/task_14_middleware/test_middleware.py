"""中间件管道测试。"""
import pytest
from request import Request, Response
from middleware import Middleware, AuthMiddleware, LoggingMiddleware, CorsMiddleware
from pipeline import Pipeline


def default_handler(req: Request) -> Response:
    return Response(200, "OK")


class TestPipelineExecutionOrder:
    def test_before_runs_in_order(self):
        """before 钩子应按添加顺序执行。"""
        log_mw = LoggingMiddleware()
        p = Pipeline()
        p.add(log_mw)
        p.add(AuthMiddleware())
        req = Request("GET", "/api/data")
        p.execute(req, default_handler)
        assert log_mw.log[0].startswith("REQ:")

    def test_after_runs_in_reverse_order(self):
        """
        关键测试：after 钩子应按逆序执行（后添加的先执行）。
        这确保内层中间件的 after 先于外层执行。
        """
        order = []
        class MW1(Middleware):
            def after(self, req, resp):
                order.append("mw1")
                return resp
        class MW2(Middleware):
            def after(self, req, resp):
                order.append("mw2")
                return resp
        class MW3(Middleware):
            def after(self, req, resp):
                order.append("mw3")
                return resp

        p = Pipeline()
        p.add(MW1())
        p.add(MW2())
        p.add(MW3())
        p.execute(Request("GET", "/"), default_handler)
        # 逆序：mw3 先执行，然后 mw2，最后 mw1
        assert order == ["mw3", "mw2", "mw1"]


class TestErrorHandling:
    def test_auth_blocks_admin_without_token(self):
        """未认证访问 /admin 应抛异常。"""
        p = Pipeline()
        p.add(AuthMiddleware())
        req = Request("GET", "/admin/dashboard")
        with pytest.raises(PermissionError):
            p.execute(req, default_handler)

    def test_auth_allows_admin_with_token(self):
        """有 token 访问 /admin 应通过。"""
        p = Pipeline()
        p.add(AuthMiddleware())
        req = Request("GET", "/admin/dashboard", headers={"Authorization": "Bearer xxx"})
        resp = p.execute(req, default_handler)
        assert resp.status == 200

    def test_auth_allows_public_without_token(self):
        """访问公开路径不需要认证。"""
        p = Pipeline()
        p.add(AuthMiddleware())
        req = Request("GET", "/api/data")
        resp = p.execute(req, default_handler)
        assert resp.status == 200

    def test_before_exception_stops_pipeline(self):
        """
        关键测试：before 钩子抛异常时应停止管道，
        后续中间件的 before 不应执行，handler 也不应调用。
        """
        order = []
        class Recorder(Middleware):
            def before(self, req):
                order.append("recorder_before")
                return req
            def after(self, req, resp):
                order.append("recorder_after")
                return resp

        p = Pipeline()
        p.add(AuthMiddleware())
        p.add(Recorder())
        req = Request("GET", "/admin/dashboard")

        with pytest.raises(PermissionError):
            p.execute(req, default_handler)

        # AuthMiddleware 的 before 抛异常后，Recorder 的 before 不应执行
        assert "recorder_before" not in order
        # after 钩子也不应执行
        assert "recorder_after" not in order


class TestMultipleMiddlewares:
    def test_cors_header_present(self):
        """CORS 头应被添加。"""
        p = Pipeline()
        p.add(CorsMiddleware())
        resp = p.execute(Request("GET", "/"), default_handler)
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"

    def test_all_middlewares_applied(self):
        """所有中间件的效果都应体现。"""
        log_mw = LoggingMiddleware()
        p = Pipeline()
        p.add(AuthMiddleware())
        p.add(log_mw)
        p.add(CorsMiddleware())
        req = Request("GET", "/api/data")
        resp = p.execute(req, default_handler)
        assert resp.status == 200
        assert resp.headers.get("X-Auth") == "checked"
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"
        assert len(log_mw.log) == 2  # REQ + RES
