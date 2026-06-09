"""模板分词器：将模板字符串拆分为 token 列表。"""
import re


class Token:
    def __init__(self, token_type: str, value: str):
        self.type = token_type
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


def tokenize(template: str) -> list:
    """
    将模板字符串分词。
    支持的语法：
    - {{ variable }} — 变量替换
    - {% for item in list %} ... {% endfor %} — 循环
    - 普通文本
    """
    tokens = []
    pos = 0

    while pos < len(template):
        # 查找 {{
        var_start = template.find("{{", pos)
        # 查找 {%
        tag_start = template.find("{%", pos)

        if var_start == -1 and tag_start == -1:
            # 剩余全是文本
            tokens.append(Token("text", template[pos:]))
            break

        # 确定哪个先出现
        if var_start == -1:
            next_start = tag_start
            is_var = False
        elif tag_start == -1:
            next_start = var_start
            is_var = True
        else:
            if var_start < tag_start:
                next_start = var_start
                is_var = True
            else:
                next_start = tag_start
                is_var = False

        # 之前的文本
        if next_start > pos:
            tokens.append(Token("text", template[pos:next_start]))

        if is_var:
            # 解析 {{ variable }}
            end = template.find("}}", next_start)
            if end == -1:
                tokens.append(Token("text", template[next_start:]))
                break
            var_name = template[next_start + 2:end].strip()
            tokens.append(Token("var", var_name))
            pos = end + 2
        else:
            # 解析 {% tag %}
            end = template.find("%}", next_start)
            if end == -1:
                tokens.append(Token("text", template[next_start:]))
                break
            tag_content = template[next_start + 2:end].strip()
            tokens.append(Token("tag", tag_content))
            pos = end + 2

    return tokens
