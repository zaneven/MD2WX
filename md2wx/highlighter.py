"""
MD2WX 纯内联微信友好代码语法着色引擎 (Python 端)
针对微信公众平台：不依赖外部 CSS 类名，直接生成带内联 style="color: ..." 的 span 标签
完美兼容微信公众号后台，支持 JavaScript/TypeScript, Python, Bash, HTML, CSS, SQL, YAML 等
"""
import re
import html

COLORS = {
    "keyword": "#f472b6",       # 关键字 (粉红)
    "string": "#34d399",        # 字符串 (薄荷绿)
    "number": "#fbbf24",        # 数字数值 (琥珀金)
    "comment": "#71717a",       # 注释 (淡灰斜体)
    "function": "#a78bfa",      # 函数名与方法 (淡紫)
    "class": "#60a5fa",         # 类名与类型 (天蓝)
    "operator": "#94a3b8",      # 运算符与标点 (灰白)
    "boolean": "#f87171",       # 布尔值与常量 (浅红)
    "variable": "#e2e8f0",      # 属性与变量 (明亮白)
}

def escape_html(text: str) -> str:
    """HTML 字符转义"""
    return html.escape(text, quote=True)

def highlight_code(code: str, lang: str = "") -> str:
    """
    对代码进行纯内联语法着色
    """
    clean_lang = (lang or "").strip().lower()

    # 纯文本/目录树等非编程语言不做任何 Token 拆分：
    # 避免把 / - . 等标点染成彩色碎片，破坏 ASCII 树结构与移动端阅读体验
    if clean_lang in ("", "text", "txt", "plain"):
        return escape_html(code)

    token_rules = []

    # 1. 注释规则
    if clean_lang in ["python", "py", "bash", "sh", "zsh", "yaml", "yml"]:
        token_rules.append(("comment", re.compile(r"#.*")))
    elif clean_lang in ["html", "xml"]:
        token_rules.append(("comment", re.compile(r"<!--[\s\S]*?-->")))
    else:
        # JS, CSS, SQL 等
        token_rules.append(("comment", re.compile(r"//.*|/\*[\s\S]*?\*/")))

    # 2. 字符串规则 (支持单双引号与反引号)
    token_rules.append(("string", re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`')))

    # 3. 数字规则
    token_rules.append(("number", re.compile(r"\b\d+(?:\.\d+)?\b")))

    # 4. 关键字规则
    if clean_lang in ["python", "py"]:
        keywords = [
            "def", "class", "return", "import", "from", "as", "if", "elif", "else",
            "for", "while", "in", "not", "and", "or", "try", "except", "finally",
            "with", "lambda", "pass", "raise", "yield", "assert", "async", "await"
        ]
    elif clean_lang in ["javascript", "js", "typescript", "ts", "jsx", "tsx"]:
        keywords = [
            "const", "let", "var", "function", "return", "if", "else", "for", "while",
            "import", "from", "export", "default", "class", "extends", "new", "this",
            "async", "await", "try", "catch", "finally", "throw", "typeof", "instanceof",
            "switch", "case", "break", "continue"
        ]
    elif clean_lang in ["bash", "sh", "zsh"]:
        keywords = [
            "if", "then", "else", "elif", "fi", "for", "while", "do", "done",
            "case", "esac", "function", "return", "exit", "echo", "cd", "export",
            "sudo", "curl", "git", "npm", "pip"
        ]
    elif clean_lang in ["sql"]:
        keywords = [
            "SELECT", "FROM", "WHERE", "INSERT", "UPDATE", "DELETE", "JOIN", "LEFT",
            "RIGHT", "INNER", "GROUP", "BY", "ORDER", "HAVING", "LIMIT", "OFFSET",
            "CREATE", "TABLE", "DROP", "ALTER", "AND", "OR", "NOT", "AS", "IN"
        ]
    elif clean_lang in ["html", "xml"]:
        keywords = ["DOCTYPE", "html", "head", "body", "div", "span", "script", "style", "link", "meta"]
    else:
        keywords = ["function", "class", "def", "return", "if", "else", "for", "while", "import", "const", "let"]

    kw_flags = re.IGNORECASE if clean_lang == "sql" else 0
    token_rules.append(("keyword", re.compile(rf"\b(?:{'|'.join(keywords)})\b", kw_flags)))

    # 5. 布尔与空值
    token_rules.append(("boolean", re.compile(r"\b(?:true|false|None|null|undefined|nil)\b", re.IGNORECASE)))

    # 6. 函数名
    token_rules.append(("function", re.compile(r"\b([a-zA-Z_]\w*)(?=\s*\()")))

    # 7. 常见操作符
    token_rules.append(("operator", re.compile(r"[-+*\/=<>!&|%?:,;.]+")))

    tokens = []
    remaining = code
    safety_counter = 0
    max_iterations = 20000

    while remaining and safety_counter < max_iterations:
        safety_counter += 1
        earliest_match = None
        match_type = None
        match_index = len(remaining)

        for t_type, regex in token_rules:
            m = regex.search(remaining)
            if m and m.start() < match_index:
                match_index = m.start()
                earliest_match = m.group(0)
                match_type = t_type

        if earliest_match is not None:
            if match_index > 0:
                tokens.append(escape_html(remaining[:match_index]))

            esc = escape_html(earliest_match)
            if match_type == "keyword":
                styled = f'<span style="color: {COLORS["keyword"]}; font-weight: 600;">{esc}</span>'
            elif match_type == "string":
                styled = f'<span style="color: {COLORS["string"]};">{esc}</span>'
            elif match_type == "number":
                styled = f'<span style="color: {COLORS["number"]};">{esc}</span>'
            elif match_type == "comment":
                styled = f'<span style="color: {COLORS["comment"]}; font-style: italic;">{esc}</span>'
            elif match_type == "function":
                styled = f'<span style="color: {COLORS["function"]};">{esc}</span>'
            elif match_type == "boolean":
                styled = f'<span style="color: {COLORS["boolean"]}; font-weight: 600;">{esc}</span>'
            elif match_type == "operator":
                styled = f'<span style="color: {COLORS["operator"]};">{esc}</span>'
            else:
                styled = esc

            tokens.append(styled)
            remaining = remaining[match_index + len(earliest_match):]
        else:
            tokens.append(escape_html(remaining))
            break

    return "".join(tokens)
