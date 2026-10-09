"""
MD2WX 双端渲染一致性测试 (Golden Consistency)

CLI 端 parser.py 与 Web 端 parser.js 是必须永远同步的两套镜像实现。
本测试以固定样例 (tests/fixtures/golden_article.md) 为输入：
  1. Node 运行 Web 端 parser.js 按全部 9 大内置主题渲染 (web/tests/render_golden.mjs)
  2. Python 端 parser.py 以相同参数渲染
  3. 归一化空白后逐主题严格比对，任一端漂移立即失败
同时校验主题单一数据源同步：md2wx/themes/*.json 与 Web 端导入清单一一对应。
Node 不可用时自动跳过 (CI 环境默认安装 Node)。
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from md2wx.parser import markdown_to_wechat_html, parse_frontmatter
from md2wx.themes import scan_themes

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_ARTICLE = Path(__file__).resolve().parent / "fixtures" / "golden_article.md"
SAMPLE_ARTICLE = PROJECT_ROOT / "sample_article.md"
RENDER_HARNESS = PROJECT_ROOT / "web" / "tests" / "render_golden.mjs"
LOADER_HOOK = PROJECT_ROOT / "web" / "tests" / "register-loader.mjs"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None or not RENDER_HARNESS.exists(),
    reason="需要 node 与 web/tests/render_golden.mjs",
)


def _normalize(html: str) -> str:
    """归一化空白差异：两端模板的换行/缩进属排版噪声，折叠后才参与严格比对"""
    html = re.sub(r">\s+<", "><", html)   # 标签间空白
    html = re.sub(r">\s+", ">", html)     # 开标签后的模板换行缩进
    html = re.sub(r"\s+</", "</", html)   # 闭合标签前的模板换行
    return re.sub(r"\s+", " ", html).strip()


def _render_web(md_path: Path) -> dict:
    """调用 Node harness 渲染 Web 端输出"""
    proc = subprocess.run(
        [
            "node",
            "--import", str(LOADER_HOOK),
            str(RENDER_HARNESS),
            str(md_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(PROJECT_ROOT / "web"),
    )
    assert proc.returncode == 0, f"Web golden harness 执行失败:\n{proc.stderr}"
    return json.loads(proc.stdout)


def _render_python(raw_md: str) -> dict:
    """Python 端按全部内置主题渲染 (与 harness 相同参数：不注入封面卡片)"""
    _, body = parse_frontmatter(raw_md)
    renders = {}
    for theme_id in sorted(scan_themes()):
        renders[theme_id] = _normalize(
            markdown_to_wechat_html(body, theme_id, insert_cover=False)
        )
    return renders


def _theme_ids() -> set:
    return set(scan_themes().keys())


def test_builtin_theme_single_source_sync():
    """主题单一数据源：md2wx/themes/*.json 与 Web 端 BUILTIN_THEMES 一一对应"""
    web = _render_web(GOLDEN_ARTICLE)
    json_ids = _theme_ids()
    web_ids = set(web["themeIds"])
    assert json_ids == web_ids, (
        f"主题双端漂移: 仅 Python 有 {sorted(json_ids - web_ids)}, "
        f"仅 Web 有 {sorted(web_ids - json_ids)}。"
        "web/src/core/themes.js 必须与 md2wx/themes/*.json 保持同步。"
    )


def test_golden_render_consistency_all_themes():
    """固定样例在全部内置主题下双端渲染产物一致"""
    web = _render_web(GOLDEN_ARTICLE)
    py_renders = _render_python(GOLDEN_ARTICLE.read_text(encoding="utf-8"))

    mismatched = []
    for theme_id in sorted(web["themes"]):
        web_html = _normalize(web["renders"][theme_id])
        py_html = py_renders[theme_id]
        if web_html != py_html:
            mismatched.append(theme_id)

    assert not mismatched, (
        f"以下主题双端渲染产物不一致: {mismatched}。"
        "parser.py 与 parser.js 为镜像实现，改动必须双端同步。"
    )


def test_golden_render_consistency_sample_article():
    """仓库标准评测样例 (sample_article.md) 双端渲染一致 (若存在)"""
    if not SAMPLE_ARTICLE.exists():
        pytest.skip("sample_article.md 不存在")
    web = _render_web(SAMPLE_ARTICLE)
    py_renders = _render_python(SAMPLE_ARTICLE.read_text(encoding="utf-8"))

    mismatched = []
    for theme_id in sorted(web["themes"]):
        if _normalize(web["renders"][theme_id]) != py_renders[theme_id]:
            mismatched.append(theme_id)
    assert not mismatched, f"sample_article.md 双端渲染不一致的主题: {mismatched}"
