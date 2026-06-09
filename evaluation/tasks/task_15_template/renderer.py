"""模板渲染器：根据 token 列表和上下文生成最终文本。"""
from context import Context
from tokenizer import Token, tokenize


class Renderer:
    def render(self, template: str, data: dict) -> str:
        """渲染模板，返回最终文本。"""
        ctx = Context(data)
        tokens = tokenize(template)
        return self._render_tokens(tokens, ctx)

    def _render_tokens(self, tokens: list, ctx: Context) -> str:
        result = []
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.type == "text":
                result.append(token.value)

            elif token.type == "var":
                value = ctx.get(token.value)
                if value == "":
                    raise KeyError(f"Undefined variable: {token.value}")
                result.append(str(value))

            elif token.type == "tag":
                if token.value.startswith("for "):
                    # 解析 for 循环
                    loop_tokens, end_idx = self._collect_loop_tokens(tokens, i)
                    result.append(self._render_for(token.value, loop_tokens, ctx))
                    i = end_idx
                    continue

            i += 1

        return "".join(result)

    def _collect_loop_tokens(self, tokens: list, start: int) -> tuple:
        """收集 for 循环体内的 token，直到 endfor。"""
        body = []
        for i in range(start + 1, len(tokens)):
            token = tokens[i]
            if token.type == "tag" and token.value == "endfor":
                return body, i
            body.append(token)
        return body, len(tokens) - 1

    def _render_for(self, tag_value: str, body_tokens: list, ctx: Context) -> str:
        """渲染 for 循环。"""
        # 解析 "for item in items"
        parts = tag_value.split()
        if len(parts) != 4 or parts[2] != "in":
            return ""

        var_name = parts[1]
        list_name = parts[3]
        items = ctx.get(list_name, [])

        if not isinstance(items, (list, tuple)):
            return ""

        result = []
        for item in items:
            ctx.push({var_name: item})
            result.append(self._render_tokens(body_tokens, ctx))
            ctx.pop()

        return "".join(result)
