"""MD2WX 命令行工具单元测试 (轻量，聚焦可离线验证的路径)"""
import io
import sys
from unittest.mock import patch

import pytest

from md2wx import cli, drafts


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


def test_cli_list_drafts_prints_items(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["md2wx", "--list-drafts", "5"])
    monkeypatch.setattr(cli, "prepare_wechat_session", lambda args: ("tok", None))
    monkeypatch.setattr(cli, "list_local_mappings", lambda: {})

    calls = {}

    def fake_list(token, count=10, token_refresher=None):
        calls["count"] = count
        return {
            "total_count": 1,
            "item_count": 1,
            "items": [{
                "media_id": "draft_media_id",
                "title": "草稿标题",
                "author": "",
                "digest": "",
                "url": "",
                "update_time": 1700000000,
                "article_count": 1,
            }],
        }

    monkeypatch.setattr(cli, "list_drafts", fake_list)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    assert calls["count"] == 5
    out = capsys.readouterr().out
    assert "草稿标题" in out
    assert "draft_media_id" in out


def test_cli_delete_draft_non_interactive_requires_yes(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["md2wx", "--delete-draft", "draft_media_id"])
    monkeypatch.setattr(sys, "stdin", io.StringIO())

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1


def test_cli_delete_draft_with_yes(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["md2wx", "--delete-draft", "draft_media_id", "-y"])
    monkeypatch.setattr(cli, "prepare_wechat_session", lambda args: ("tok", None))

    deleted = []
    monkeypatch.setattr(cli, "delete_draft", lambda token, media_id, token_refresher=None: deleted.append(media_id) or {})
    monkeypatch.setattr(cli, "forget_draft", lambda media_id: 1)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    assert deleted == ["draft_media_id"]
    assert "已同步清除 1 条本地发布记录" in capsys.readouterr().out


def test_cli_update_flags_require_publish(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["md2wx", "post.md", "--update-draft", "draft_media_id"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1


def test_cli_update_and_new_draft_conflict(monkeypatch):
    monkeypatch.setattr(
        sys, "argv",
        ["md2wx", "post.md", "-p", "--update-draft", "draft_media_id", "--new-draft"],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1


def _write_post(tmp_path):
    md = tmp_path / "post.md"
    md.write_text("---\ntitle: 续更标题\ndigest: 摘要\n---\n\n# 续更标题\n\n正文段落。\n", encoding="utf-8")
    return md


def test_cli_dry_run_auto_updates_previous_draft(tmp_path, monkeypatch, capsys):
    md = _write_post(tmp_path)
    monkeypatch.setattr(drafts, "DRAFT_STATE_PATH", tmp_path / "drafts.json")
    key = drafts.draft_state_key(str(md))
    drafts.record_last_draft(key, "prev_draft_id", "续更标题")

    monkeypatch.setattr(sys, "argv", ["md2wx", str(md), "-p", "--dry-run", "--no-cover"])
    monkeypatch.setattr(cli, "resolve_wechat_credentials", lambda args: ("app_id", "app_secret"))

    def _forbidden_urlopen(*a, **kw):
        raise AssertionError("dry-run 不应发起网络请求")

    with patch("urllib.request.urlopen", side_effect=_forbidden_urlopen):
        cli.main()

    out = capsys.readouterr().out
    assert "draft/update" in out
    assert "prev_draft_id" in out


def test_cli_dry_run_new_draft_ignores_mapping(tmp_path, monkeypatch, capsys):
    md = _write_post(tmp_path)
    monkeypatch.setattr(drafts, "DRAFT_STATE_PATH", tmp_path / "drafts.json")
    drafts.record_last_draft(drafts.draft_state_key(str(md)), "prev_draft_id", "续更标题")

    monkeypatch.setattr(sys, "argv", ["md2wx", str(md), "-p", "--dry-run", "--no-cover", "--new-draft"])
    monkeypatch.setattr(cli, "resolve_wechat_credentials", lambda args: ("app_id", "app_secret"))

    def _forbidden_urlopen(*a, **kw):
        raise AssertionError("dry-run 不应发起网络请求")

    with patch("urllib.request.urlopen", side_effect=_forbidden_urlopen):
        cli.main()

    out = capsys.readouterr().out
    assert "draft/add" in out
    assert "prev_draft_id" not in out


def test_cli_dry_run_explicit_update_draft(tmp_path, monkeypatch, capsys):
    md = _write_post(tmp_path)
    monkeypatch.setattr(drafts, "DRAFT_STATE_PATH", tmp_path / "drafts.json")
    monkeypatch.setattr(
        sys, "argv",
        ["md2wx", str(md), "-p", "--dry-run", "--no-cover", "--update-draft", "manual_draft_id"],
    )
    monkeypatch.setattr(cli, "resolve_wechat_credentials", lambda args: ("app_id", "app_secret"))

    def _forbidden_urlopen(*a, **kw):
        raise AssertionError("dry-run 不应发起网络请求")

    with patch("urllib.request.urlopen", side_effect=_forbidden_urlopen):
        cli.main()

    out = capsys.readouterr().out
    assert "draft/update" in out
    assert "manual_draft_id" in out


# ---------------------------------------------------------------------------
# 波次一 (v1.9.0)：发布门禁与机器可读输出
# ---------------------------------------------------------------------------
def _write_risky_post(tmp_path):
    md = tmp_path / "risky.md"
    md.write_text(
        "---\ntitle: " + "超" * 26 + "\ndigest: 摘要\n---\n\n# " + "超" * 26 + "\n\n正文。\n",
        encoding="utf-8",
    )
    return md


def test_cli_publish_gate_blocks_before_any_network(tmp_path, monkeypatch, capsys):
    md = _write_risky_post(tmp_path)
    monkeypatch.setattr(sys, "argv", ["md2wx", str(md), "-p"])

    def _forbidden(*a, **kw):
        raise AssertionError("发布门禁拦截时不应发起任何网络请求")

    monkeypatch.setattr(cli, "resolve_wechat_credentials", _forbidden)
    monkeypatch.setattr(cli, "get_access_token", _forbidden)
    with patch("urllib.request.urlopen", side_effect=_forbidden):
        with pytest.raises(SystemExit) as exc:
            cli.main()

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "中止发布" in err
    assert "--no-lint" in err


def test_cli_no_lint_escape_hatch_allows_dry_run(tmp_path, monkeypatch, capsys):
    md = _write_risky_post(tmp_path)
    monkeypatch.setattr(
        sys, "argv",
        ["md2wx", str(md), "-p", "--dry-run", "--no-cover", "--no-lint"],
    )
    monkeypatch.setattr(cli, "resolve_wechat_credentials", lambda args: ("app_id", "app_secret"))

    with patch("urllib.request.urlopen", side_effect=AssertionError("dry-run 不应联网")):
        cli.main()

    out = capsys.readouterr().out
    assert "[DRY RUN]" in out


def test_cli_lint_json_output_is_parseable(tmp_path, monkeypatch, capsys):
    md = tmp_path / "bad.md"
    md.write_text(
        "---\ntitle: " + "超" * 25 + "\ndigest: 摘要混用半角逗号,触发规则\n---\n\n正文,混用。\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["md2wx", str(md), "--lint", "--format", "json"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
    import json

    payload = json.loads(capsys.readouterr().out)
    codes = [item["code"] for item in payload["issues"]]
    assert "title-too-long" in codes
    assert payload["summary"]["errors"] >= 1
    assert payload["file"].endswith("bad.md")


def test_collect_external_links_skips_images_code_and_duplicates():
    from md2wx.linter import collect_external_links

    md = (
        "![图](https://cdn.example.com/a.png)\n"
        "[官网](https://example.com/docs)\n"
        "重复 [再来](https://example.com/docs)\n"
        "`https://code.example.com` 不算\n"
    )
    links = collect_external_links(md)
    assert [url for url, _ in links] == ["https://example.com/docs"]
