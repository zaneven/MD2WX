"""MD2WX 命令行工具单元测试 (轻量，聚焦可离线验证的路径)"""
import sys
from unittest.mock import patch

import pytest

from md2wx import cli


def test_load_env_credentials_filters_placeholders(monkeypatch):
    monkeypatch.setattr(cli, "load_env", lambda: {
        "WECHAT_APP_ID": "wx123",
        "WECHAT_APP_SECRET": "your_secret_here",
    })
    creds = cli.load_env_credentials()
    assert creds == {"app_id": "wx123", "app_secret": ""}


def test_cli_lint_clean_file_exits_zero(tmp_path, monkeypatch, capsys):
    md = tmp_path / "ok.md"
    md.write_text("---\ntitle: 短标题\ndigest: 合格摘要\n---\n\n正文\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["md2wx", str(md), "--lint"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    assert "全部通过" in capsys.readouterr().out


def test_cli_lint_error_file_exits_one(tmp_path, monkeypatch, capsys):
    md = tmp_path / "bad.md"
    md.write_text(
        "---\ntitle: " + "超" * 25 + "\ndigest: " + "长" * 60 + "\n---\n\n正文\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["md2wx", str(md), "--lint"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "title-too-long" in out or "20 字" in out


def test_cli_lint_missing_file_exits_one(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["md2wx", str(tmp_path / "nope.md"), "--lint"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1


def test_wechat_length_constants():
    """微信平台硬上限常量不回退"""
    assert cli.WECHAT_TITLE_MAX_LEN == 64
    assert cli.WECHAT_DIGEST_MAX_LEN == 120


def test_copy_html_to_clipboard_non_macos_returns_false():
    with patch.object(cli.sys, "platform", "linux"):
        assert cli.copy_html_to_clipboard("<p>x</p>") is False


def test_cli_dry_run_prints_payload_without_network(tmp_path, monkeypatch, capsys):
    """--dry-run 完成渲染与封面解析，打印 payload 摘要且不触发任何微信网络请求"""
    md = tmp_path / "post.md"
    md.write_text(
        "---\ntitle: 演练标题\ndigest: 演练摘要\n---\n\n# 演练标题\n\n正文段落。\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["md2wx", str(md), "-p", "--dry-run", "--no-cover"])

    def _forbidden_urlopen(*a, **kw):
        raise AssertionError("dry-run 模式不应发起任何网络请求")

    with patch("urllib.request.urlopen", side_effect=_forbidden_urlopen):
        cli.main()

    out = capsys.readouterr().out
    assert "[DRY RUN]" in out
    assert "演练标题" in out
    assert "digest" in out
    assert "未上传素材、未推送草稿" in out
