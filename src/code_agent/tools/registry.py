from code_agent.tools.read import tool_read_file, tool_list_dir
from code_agent.tools.edit import tool_write_file, tool_str_replace, tool_replace_function
from code_agent.tools.search import tool_search_text
from code_agent.tools.execute import tool_execute, tool_run_pytest

from code_agent.indexer.ast_index import ASTIndex
_ast_index = ASTIndex()


def init_index(root: str = ".") -> str:
    """启动时调用，扫描项目建立 AST 索引（含意图摘要）。"""
    _ast_index.index_repo(root)
    return f"✅ 索引完成：{_ast_index.stats()}"


# AST 工具包装函数
def tool_search_class(class_name: str) -> str:
    return _ast_index.search_class(class_name)

def tool_search_method(method_name: str) -> str:
    return _ast_index.search_method(method_name)

def tool_search_method_in_class(method_name: str, class_name: str) -> str:
    return _ast_index.search_method_in_class(method_name, class_name)

def tool_search_method_in_file(method_name: str, filepath: str) -> str:
    return _ast_index.search_method_in_file(method_name, filepath)

def tool_get_file_symbols(filepath: str) -> str:
    return _ast_index.get_file_symbols(filepath)

# P3 新增：语义层查询
def tool_search_intent(query: str) -> str:
    return _ast_index.search_intent(query)

def tool_list_file_summaries() -> str:
    return _ast_index.list_file_summaries()


TOOL_FUNCTIONS = {
    "read_file":              tool_read_file,
    "list_dir":               tool_list_dir,
    "write_file":             tool_write_file,
    "str_replace":            tool_str_replace,
    "replace_function":       tool_replace_function,   # P4 新增
    "search_text":            tool_search_text,
    "execute":                tool_execute,
    "run_pytest":             tool_run_pytest,
    "search_class":           tool_search_class,
    "search_method":          tool_search_method,
    "search_method_in_class": tool_search_method_in_class,
    "search_method_in_file":  tool_search_method_in_file,
    "get_file_symbols":       tool_get_file_symbols,
    "search_intent":          tool_search_intent,       # P3 新增
    "list_file_summaries":    tool_list_file_summaries, # P3 新增
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取文件内容，每次最多显示 100 行，支持分页",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":   {"type": "string", "description": "文件路径"},
                    "offset": {"type": "integer", "description": "从第几行开始读，默认 0"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "列出目录下的文件和子目录，用于了解项目结构",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径，默认当前目录"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "创建或覆盖写入文件，适合创建新文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "文件内容"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "str_replace",
            "description": "精确替换文件中的某段内容，比覆盖写入更安全",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "文件路径"},
                    "old_str": {"type": "string", "description": "要被替换的原始内容（必须与文件完全一致）"},
                    "new_str": {"type": "string", "description": "替换后的新内容"}
                },
                "required": ["path", "old_str", "new_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": "在项目中搜索包含指定关键词的代码行（全文搜索）",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern":   {"type": "string", "description": "搜索关键词或正则表达式"},
                    "path":      {"type": "string", "description": "搜索目录，默认当前目录"},
                    "file_glob": {"type": "string", "description": "文件过滤，默认 *.py"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute",
            "description": "执行 shell 命令，内置危险命令拦截和超时保护",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的命令"},
                    "cwd":     {"type": "string", "description": "工作目录，默认当前目录"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_pytest",
            "description": "运行 pytest 测试，返回测试结果",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":       {"type": "string", "description": "测试文件或目录，默认当前目录"},
                    "extra_args": {"type": "string", "description": "额外参数，默认 -v --tb=short"}
                },
                "required": []
            }
        }
    },
    # M4 新增：AST 结构化查询工具
    {
        "type": "function",
        "function": {
            "name": "search_class",
            "description": "在项目中按类名查找类，返回类的位置和方法列表（比 search_text 更精确）",
            "parameters": {
                "type": "object",
                "properties": {
                    "class_name": {"type": "string", "description": "类名，例如 Calculator"}
                },
                "required": ["class_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_method",
            "description": "在项目中按函数名查找函数或方法，返回所在文件和行号",
            "parameters": {
                "type": "object",
                "properties": {
                    "method_name": {"type": "string", "description": "函数名，例如 divide"}
                },
                "required": ["method_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_method_in_class",
            "description": "在指定类中查找方法",
            "parameters": {
                "type": "object",
                "properties": {
                    "method_name": {"type": "string", "description": "方法名"},
                    "class_name":  {"type": "string", "description": "类名"}
                },
                "required": ["method_name", "class_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_method_in_file",
            "description": "在指定文件中查找函数",
            "parameters": {
                "type": "object",
                "properties": {
                    "method_name": {"type": "string", "description": "函数名"},
                    "filepath":    {"type": "string", "description": "文件路径"}
                },
                "required": ["method_name", "filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_symbols",
            "description": "列出一个文件里所有的类和函数，快速了解文件结构",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "文件路径"}
                },
                "required": ["filepath"]
            }
        }
    },
    # P4 新增：AST 级别函数替换（比 str_replace 更稳健）
    {
        "type": "function",
        "function": {
            "name": "replace_function",
            "description": (
                "用函数名定位并替换整个函数体，比 str_replace 更稳健——"
                "不受空格/缩进变化影响。适合替换已知函数名的完整实现。"
                "支持 'ClassName.method_name' 格式指定类方法。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path":      {"type": "string", "description": "文件路径"},
                    "func_name": {"type": "string", "description": "函数名，如 divide 或 Calculator.divide"},
                    "new_body":  {"type": "string", "description": "新的完整函数定义（包含 def 行）"}
                },
                "required": ["path", "func_name", "new_body"]
            }
        }
    },
    # P3 新增：语义层查询（自然语言找文件）
    {
        "type": "function",
        "function": {
            "name": "search_intent",
            "description": (
                "用自然语言描述查找相关文件，比 search_text 更适合'我想找处理XX功能的文件'这类问题。"
                "例如：search_intent('日期解析') 能找到 date_utils.py。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "自然语言描述，如'除法运算'、'用户认证'"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_file_summaries",
            "description": "列出项目中所有已索引文件的意图摘要，快速了解整个项目的模块分布",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
]


def dispatch(tool_name: str, tool_args: dict) -> str:
    """根据工具名找到对应函数并执行，返回结果字符串。"""
    func = TOOL_FUNCTIONS.get(tool_name)
    if func is None:
        return f"❌ 未知工具：{tool_name}，可用工具：{list(TOOL_FUNCTIONS.keys())}"
    try:
        return func(**tool_args)
    except TypeError as e:
        return f"❌ 工具参数错误：{e}"
    except Exception as e:
        return f"❌ 工具执行出错：{e}"
