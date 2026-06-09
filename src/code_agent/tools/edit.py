import ast
import textwrap
from pathlib import Path


def _check_syntax(code: str) -> str | None:
    """检查 Python 语法，返回错误信息，无错误返回 None。"""
    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return f"语法错误：第 {e.lineno} 行 - {e.msg}"


def tool_write_file(path: str, content: str) -> str:
    """整个文件覆盖写入，适合创建新文件。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if path.endswith(".py"):
        err = _check_syntax(content)
        if err:
            return f"❌ 写入被拒绝，{err}\n请修正后重试。"
    p.write_text(content, encoding="utf-8")
    return f"✅ 文件已写入：{path}（共 {len(content.splitlines())} 行）"


def tool_str_replace(path: str, old_str: str, new_str: str) -> str:
    """
    精确字符串替换：在文件中找到 old_str，替换为 new_str。
    来自论文资料 6/11 的强收敛设计。
    """
    p = Path(path)
    if not p.exists():
        return f"❌ 文件不存在：{path}"

    content = p.read_text(encoding="utf-8")
    count = content.count(old_str)
    if count == 0:
        return (
            "❌ 未找到要替换的内容，请重新读取文件确认原文。\n"
            "提示：注意空格、缩进、换行是否与文件完全一致。"
        )
    if count > 1:
        return (
            f"❌ 找到 {count} 处匹配，无法确定替换哪一处。\n"
            "请提供更多上下文使 old_str 唯一。"
        )

    new_content = content.replace(old_str, new_str, 1)
    if path.endswith(".py"):
        err = _check_syntax(new_content)
        if err:
            return f"❌ 替换被拒绝，替换后代码存在{err}\n请修正 new_str 后重试。"

    p.write_text(new_content, encoding="utf-8")
    return f"✅ 替换成功：{path}"


def tool_replace_function(path: str, func_name: str, new_body: str) -> str:
    """
    P4 新增（来自论文 CodeStruct）：AST 级别的函数替换。

    用函数名定位，而不是用文本内容定位——不受空格/缩进变化影响。

    比喻：str_replace 是"找到这段文字再替换"（脆弱），
    tool_replace_function 是"找到这个函数再替换"（稳健）。

    参数：
    - path：文件路径
    - func_name：要替换的函数名（支持 "ClassName.method_name" 格式）
    - new_body：新的完整函数定义（包含 def 行）
    """
    p = Path(path)
    if not p.exists():
        return f"❌ 文件不存在：{path}"

    source = p.read_text(encoding="utf-8")

    # 解析目标函数名（支持 Class.method 格式）
    target_class = None
    target_func  = func_name
    if "." in func_name:
        target_class, target_func = func_name.rsplit(".", 1)

    # 先检查新函数体语法
    err = _check_syntax(new_body)
    if err:
        return f"❌ new_body 语法错误：{err}\n请修正后重试。"

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return f"❌ 原文件语法错误，无法解析：{e}"

    # 找到目标函数节点
    target_node = _find_function_node(tree, target_func, target_class)
    if target_node is None:
        hint = f"类 {target_class} 中的 " if target_class else ""
        return (
            f"❌ 未找到{hint}函数 `{target_func}`。\n"
            f"提示：可用 get_file_symbols('{path}') 查看文件中所有函数名。"
        )

    # 用行号定位原函数在源码中的位置
    lines = source.splitlines(keepends=True)
    start_line = target_node.lineno - 1        # 转为 0-indexed
    end_line   = getattr(target_node, "end_lineno", target_node.lineno)  # 1-indexed

    # 保留原函数的缩进级别
    original_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
    indent_str = " " * original_indent

    # 对 new_body 重新缩进，匹配原函数的缩进
    new_body_dedented = textwrap.dedent(new_body)
    new_body_indented = textwrap.indent(new_body_dedented, indent_str)
    if not new_body_indented.endswith("\n"):
        new_body_indented += "\n"

    # 替换对应行
    new_lines = lines[:start_line] + [new_body_indented] + lines[end_line:]
    new_source = "".join(new_lines)

    # 最终语法检查
    err = _check_syntax(new_source)
    if err:
        return f"❌ 替换后文件语法错误：{err}\n请检查 new_body 的缩进和语法。"

    p.write_text(new_source, encoding="utf-8")
    return f"✅ 函数 `{func_name}` 替换成功：{path}"


def _find_function_node(
    tree: ast.AST,
    func_name: str,
    class_name: str | None
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """在 AST 中找到目标函数节点。"""
    for node in ast.walk(tree):
        if class_name and isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in ast.walk(node):
                if (isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and child.name == func_name):
                    return child
        elif not class_name:
            if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == func_name):
                return node
    return None
