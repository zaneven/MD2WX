"""
MD2WX 主题管理引擎
支持 JSON 主题文件动态发现、组件风格化渲染配置与用户级自定义扩展
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Union, Optional

DEFAULT_THEME_ID = "tech-blue"

# 内置核心保底基准配置 (当极端情况下文件不可用或字段缺失时的终极兜底)
FALLBACK_BASE_THEME: Dict[str, Any] = {
    "id": "tech-blue",
    "name": "现代科技蓝 (默认)",
    "description": "沉稳极客科技风，适合开发者手记、架构复盘与前沿技术干货",
    "colors": {
        "accent": "#2563eb",
        "accent_bg": "#eff6ff",
        "text_color": "#27272a",
        "sub_color": "#71717a",
        "border_color": "#e4e4e7",
        "code_bg": "#18181b",
        "code_text": "#e4e4e7",
        "quote_bg": "#f4f4f5",
        "page_bg": "#ffffff",
    },
    "typography": {
        "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
        "font_size_base": "15.5px",
        "line_height_base": "1.8",
        "letter_spacing": "0.4px",
        "paragraph_indent": False,
    },
    "styles": {
        "container": "clean",
        "h1": "underline",
        "h2": "left_bar",
        "h3": "diamond",
        "quote": "left_stripe",
        "code": "mac_dark",
        "table": "zebra",
        "list": "bullet",
        "hr": "line",
    }
}

def deep_merge(base: dict, override: dict) -> dict:
    """深度递归合并字典"""
    merged = base.copy()
    for k, v in override.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged

def _wrap_theme_compatibility(theme: dict) -> dict:
    """
    为主题数据注入向后兼容层：
    既支持层级访问 theme["colors"]["accent"] / theme["styles"]["h2"]
    也支持旧版扁平访问 theme["accent"] / theme["quote_bg"]
    """
    result = dict(theme)
    colors = result.get("colors", {})
    for color_key, color_val in colors.items():
        if color_key not in result:
            result[color_key] = color_val

    typography = result.get("typography", {})
    for typo_key, typo_val in typography.items():
        if typo_key not in result:
            result[typo_key] = typo_val

    styles = result.get("styles", {})
    for style_key, style_val in styles.items():
        flat_key = f"{style_key}_style"
        if flat_key not in result:
            result[flat_key] = style_val

    return result

def load_theme_file(file_path: Union[str, Path]) -> dict:
    """
    加载并解析单个 JSON 主题文件，并进行兜底合并与兼容性包装
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"主题文件不存在: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 深度合并基准配置，确保缺省字段安全兜底
    merged = deep_merge(FALLBACK_BASE_THEME, data)
    if "id" not in data:
        merged["id"] = path.stem
    if "name" not in data:
        merged["name"] = path.stem
    merged["_source_path"] = str(path)

    return _wrap_theme_compatibility(merged)

def get_builtin_themes_dir() -> Path:
    """获取内置主题目录"""
    return Path(__file__).parent / "themes"

def get_user_themes_dir() -> Path:
    """获取用户自定义主题配置目录 (~/.config/md2wx/themes)"""
    return Path.home() / ".config" / "md2wx" / "themes"

def scan_themes() -> Dict[str, dict]:
    """
    全量扫描可用主题：
    优先级：内置主题 -> 用户目录主题 (同名可覆盖)
    """
    discovered: Dict[str, dict] = {}

    # 1. 扫描内置主题
    builtin_dir = get_builtin_themes_dir()
    if builtin_dir.exists() and builtin_dir.is_dir():
        for json_file in sorted(builtin_dir.glob("*.json")):
            try:
                t = load_theme_file(json_file)
                discovered[t["id"]] = t
            except Exception as e:
                # 容错跳过无效文件
                pass

    # 2. 扫描用户自定义目录 ~/.config/md2wx/themes/
    user_dir = get_user_themes_dir()
    if user_dir.exists() and user_dir.is_dir():
        for json_file in sorted(user_dir.glob("*.json")):
            try:
                t = load_theme_file(json_file)
                discovered[t["id"]] = t
            except Exception:
                pass

    # 保证 tech-blue 始终就绪
    if DEFAULT_THEME_ID not in discovered:
        discovered[DEFAULT_THEME_ID] = _wrap_theme_compatibility(FALLBACK_BASE_THEME)

    return discovered

# 全局预加载主题字典，保证外部直接引用 from md2wx.themes import THEMES 正常工作
THEMES: Dict[str, dict] = scan_themes()

def refresh_themes() -> Dict[str, dict]:
    """重新扫描并刷新内存中的主题缓存"""
    global THEMES
    THEMES = scan_themes()
    return THEMES

def list_themes() -> Dict[str, dict]:
    """返回当前已注册的所有主题清单"""
    return THEMES or scan_themes()

def get_theme(name_or_path: str = DEFAULT_THEME_ID) -> dict:
    """
    根据主题标识符或外部 JSON 文件路径获取主题配置：
    1. 若 name_or_path 是一个有效的 JSON 文件路径，直接加载并返回；
    2. 否则在已扫描的主题列表中检索；
    3. 若检索不到，安全回退到默认的科技蓝 (tech-blue) 主题。
    """
    if not name_or_path:
        name_or_path = DEFAULT_THEME_ID

    # 1. 优先判断是否为具体文件路径
    candidate_path = Path(name_or_path).expanduser()
    if candidate_path.exists() and candidate_path.is_file():
        try:
            return load_theme_file(candidate_path)
        except Exception:
            pass

    # 2. 在已注册主题中查找
    themes_map = list_themes()
    if name_or_path in themes_map:
        return themes_map[name_or_path]

    # 3. 再次尝试局部刷新查找
    refreshed = refresh_themes()
    if name_or_path in refreshed:
        return refreshed[name_or_path]

    # 4. 终极回退
    return refreshed.get(DEFAULT_THEME_ID, _wrap_theme_compatibility(FALLBACK_BASE_THEME))
