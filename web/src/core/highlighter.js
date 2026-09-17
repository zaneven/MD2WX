/**
 * MD2WX Studio - 纯内联微信友好代码语法着色引擎
 * 针对微信公众平台：不依赖外部 CSS 类名，直接生成带内联 style="color: ..." 的 span 标签
 * 支持语言：JavaScript/TypeScript, Python, Bash/Shell, HTML/XML, CSS, JSON, SQL, 通用代码
 */

// 高质感语法色彩定义 (适配深色/终端代码背景)
const COLORS = {
  keyword: '#f472b6',       // 关键字 (粉红)
  string: '#34d399',        // 字符串 (薄荷绿)
  number: '#fbbf24',        // 数字数值 (琥珀金)
  comment: '#71717a',       // 注释 (淡灰斜体)
  function: '#a78bfa',      // 函数名与方法 (淡紫)
  class: '#60a5fa',         // 类名与类型 (天蓝)
  operator: '#94a3b8',      // 运算符与标点 (灰白)
  boolean: '#f87171',       // 布尔值与常量 (浅红)
  variable: '#e2e8f0',      // 属性与变量 (明亮白)
};

/**
 * HTML 特殊字符转义
 */
function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/**
 * 对代码进行词法高亮
 * @param {string} code 源代码
 * @param {string} lang 语言标识 (python, js, html, css, bash, json 等)
 * @returns {string} 注入内联样式的 HTML 字符串
 */
export function highlightCode(code, lang = '') {
  const cleanLang = (lang || '').trim().toLowerCase();
  
  // 简易 Tokenizer 规则表
  const tokenRules = [];

  // 通用注释
  if (['python', 'bash', 'sh', 'zsh', 'yaml', 'yml'].includes(cleanLang)) {
    tokenRules.push({ type: 'comment', regex: /#.*/ });
  } else if (['html', 'xml'].includes(cleanLang)) {
    tokenRules.push({ type: 'comment', regex: /<!--[\s\S]*?-->/ });
  } else {
    // JS, CSS, SQL, 其它 C-style 注释
    tokenRules.push({ type: 'comment', regex: /\/\/.*|\/\*[\s\S]*?\*\// });
  }

  // 字符串规则 (支持单双引号与反引号)
  tokenRules.push({ type: 'string', regex: /"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`/ });

  // 数字规则
  tokenRules.push({ type: 'number', regex: /\b\d+(?:\.\d+)?\b/ });

  // 语言特定关键字
  let keywords = [];
  if (['python', 'py'].includes(cleanLang)) {
    keywords = [
      'def', 'class', 'return', 'import', 'from', 'as', 'if', 'elif', 'else',
      'for', 'while', 'in', 'not', 'and', 'or', 'try', 'except', 'finally',
      'with', 'lambda', 'pass', 'raise', 'yield', 'assert', 'async', 'await'
    ];
  } else if (['javascript', 'js', 'typescript', 'ts', 'jsx', 'tsx'].includes(cleanLang)) {
    keywords = [
      'const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while',
      'import', 'from', 'export', 'default', 'class', 'extends', 'new', 'this',
      'async', 'await', 'try', 'catch', 'finally', 'throw', 'typeof', 'instanceof',
      'switch', 'case', 'break', 'continue'
    ];
  } else if (['bash', 'sh', 'zsh'].includes(cleanLang)) {
    keywords = [
      'if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'do', 'done',
      'case', 'esac', 'function', 'return', 'exit', 'echo', 'cd', 'export',
      'sudo', 'curl', 'git', 'npm', 'pip'
    ];
  } else if (['sql'].includes(cleanLang)) {
    keywords = [
      'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'JOIN', 'LEFT',
      'RIGHT', 'INNER', 'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET',
      'CREATE', 'TABLE', 'DROP', 'ALTER', 'AND', 'OR', 'NOT', 'AS', 'IN'
    ];
  } else if (['html', 'xml'].includes(cleanLang)) {
    keywords = ['DOCTYPE', 'html', 'head', 'body', 'div', 'span', 'script', 'style', 'link', 'meta'];
  } else {
    // 通用常见关键字
    keywords = ['function', 'class', 'def', 'return', 'if', 'else', 'for', 'while', 'import', 'const', 'let'];
  }

  // 构造关键字正则
  if (keywords.length > 0) {
    const kwRegex = new RegExp(`\\b(?:${keywords.join('|')})\\b`, cleanLang === 'sql' ? 'i' : '');
    tokenRules.push({ type: 'keyword', regex: kwRegex });
  }

  // 布尔值与空值
  tokenRules.push({ type: 'boolean', regex: /\b(?:true|false|None|null|undefined|nil)\b/ });

  // 函数调用识别 (如 funcName(...) )
  tokenRules.push({ type: 'function', regex: /\b([a-zA-Z_]\w*)(?=\s*\()/ });

  // 操作符
  tokenRules.push({ type: 'operator', regex: /[-+*\/=<>!&|%?:,;.]+/ });

  // 逐段拆解与替换
  const tokens = [];
  let remaining = code;
  let safetyCounter = 0;
  const maxIterations = 20000;

  while (remaining.length > 0 && safetyCounter++ < maxIterations) {
    let earliestMatch = null;
    let matchType = null;
    let matchIndex = remaining.length;

    for (const rule of tokenRules) {
      const match = rule.regex.exec(remaining);
      if (match && match.index < matchIndex) {
        matchIndex = match.index;
        earliestMatch = match[0];
        matchType = rule.type;
      }
    }

    if (earliestMatch !== null) {
      // 匹配前的前缀文本 (普通代码)
      if (matchIndex > 0) {
        tokens.push(escapeHtml(remaining.substring(0, matchIndex)));
      }

      // 格式化当前 Token
      const esc = escapeHtml(earliestMatch);
      let styledSpan = esc;

      if (matchType === 'keyword') {
        styledSpan = `<span style="color: ${COLORS.keyword}; font-weight: 600;">${esc}</span>`;
      } else if (matchType === 'string') {
        styledSpan = `<span style="color: ${COLORS.string};">${esc}</span>`;
      } else if (matchType === 'number') {
        styledSpan = `<span style="color: ${COLORS.number};">${esc}</span>`;
      } else if (matchType === 'comment') {
        styledSpan = `<span style="color: ${COLORS.comment}; font-style: italic;">${esc}</span>`;
      } else if (matchType === 'function') {
        styledSpan = `<span style="color: ${COLORS.function};">${esc}</span>`;
      } else if (matchType === 'boolean') {
        styledSpan = `<span style="color: ${COLORS.boolean}; font-weight: 600;">${esc}</span>`;
      } else if (matchType === 'operator') {
        styledSpan = `<span style="color: ${COLORS.operator};">${esc}</span>`;
      }

      tokens.push(styledSpan);
      remaining = remaining.substring(matchIndex + earliestMatch.length);
    } else {
      // 剩余全为普通文本
      tokens.push(escapeHtml(remaining));
      break;
    }
  }

  return tokens.join('');
}
