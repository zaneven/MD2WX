"""
双端 Lint 一致性测试 (Lint Consistency)

CLI 端 md2wx/linter.py 与 Web 端 web/src/core/lint.js 是必须永远同步的两套镜像实现。
本测试以固定语料为输入：
  1. Node 运行 web/tests/lint_report.mjs 产出 Web 端问题清单
  2. Python 端 lint_markdown 产出 CLI 端问题清单
  3. 逐条严格比对 code / level / message / line，任一端漂移立即失败
Node 不可用时自动跳过 (CI 环境默认安装 Node)。
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from md2wx.linter import lint_markdown

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LINT_HARNESS = PROJECT_ROOT / "web" / "tests" / "lint_report.mjs"
LOADER_HOOK = PROJECT_ROOT / "web" / "tests" / "register-loader.mjs"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None or not LINT_HARNESS.exists(),
    reason="需要 node 与 web/tests/lint_report.mjs",
)


def _lint_web(md_path: Path) -> list:
    """调用 Node harness 产出 Web 端 lint 问题清单"""
    proc = subprocess.run(
        [
            "node",
            "--import", str(LOADER_HOOK),
            str(LINT_HARNESS),
            str(md_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(PROJECT_ROOT / "web"),
    )
    assert proc.returncode == 0, f"Web lint harness 执行失败:\n{proc.stderr}"
    return json.loads(proc.stdout)["issues"]


def _lint_corpus() -> list:
    corpus = [PROJECT_ROOT / "sample_article.md", FIXTURES / "lint_corpus.md"]
    corpus.extend(sorted(FIXTURES.glob("golden_*.md")))
    return [path for path in corpus if path.exists()]


def test_lint_issue_codes_and_lines_match_python():
    """全部语料在 CLI 与 Web 端产出的问题清单逐条一致 (含行号与文案)"""
    mismatched = []
    for md_path in _lint_corpus():
        web_issues = _lint_web(md_path)
        py_issues = lint_markdown(md_path.read_text(encoding="utf-8"))
        if web_issues != py_issues:
            mismatched.append(md_path.name)
            print(f"\n[{md_path.name}] Web: {web_issues}")
            print(f"[{md_path.name}] Py : {py_issues}")
    assert not mismatched, (
        f"以下语料的双端 lint 结果不一致: {mismatched}。"
        "linter.py 与 lint.js 为镜像实现，改动必须双端同步。"
    )


def test_lint_consistency_on_control_chars_crlf_and_emoji(tmp_path):
    """控制字符 / CRLF / Emoji / 未闭合标签等边界输入双端一致"""
    md = (
        "---\r\n"
        "title: 边界标题混用(半角)\r\n"
        "digest: 摘要混用半角逗号,触发标点规则\r\n"
        "---\r\n"
        "\r\n"
        "# 边界标题混用(半角)\r\n"
        "\r\n"
        "正文含控制字符\x00与表情 😀。\r\n"
        "\r\n"
        "<div>未闭合容器\r\n"
    )
    md_path = tmp_path / "edge_lint.md"
    md_path.write_text(md, encoding="utf-8")

    assert _lint_web(md_path) == lint_markdown(md)


def test_lint_corpus_covers_extended_rules():
    """确认语料确实覆盖了波次一新增规则，避免一致性测试形同虚设"""
    codes = {item["code"] for item in lint_markdown((FIXTURES / "lint_corpus.md").read_text(encoding="utf-8"))}
    expected = {
        "title-too-long",
        "cover-forbidden",
        "emoji-banned",
        "html-unclosed",
        "link-format-invalid",
        "punctuation-mixed",
    }
    assert expected <= codes
