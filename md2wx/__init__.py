"""
MD2WX: Markdown to WeChat Official Account Formatter
将 Markdown 转换成微信公众号高质感内联样式的转换工具与自动化发布套件
"""

from .parser import markdown_to_wechat_html, parse_frontmatter, strip_markdown
from .themes import (
    get_theme,
    list_themes,
    load_theme_file,
    refresh_themes,
    get_builtin_themes_dir,
    get_user_themes_dir,
    THEMES,
)
from .uploader import get_access_token, upload_image_to_wechat_cdn, upload_cover_material
from .publisher import publish_draft_to_wechat

__version__ = "1.1.1"

__all__ = [
    "markdown_to_wechat_html",
    "parse_frontmatter",
    "strip_markdown",
    "get_theme",
    "list_themes",
    "load_theme_file",
    "refresh_themes",
    "get_builtin_themes_dir",
    "get_user_themes_dir",
    "THEMES",
    "get_access_token",
    "upload_image_to_wechat_cdn",
    "upload_cover_material",
    "publish_draft_to_wechat",
]
