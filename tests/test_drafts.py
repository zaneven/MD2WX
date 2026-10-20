"""MD2WX 微信草稿箱管理服务单元测试 (列表 / 更新 / 删除 / 本地映射)"""
import io
import json
import time
from pathlib import Path
from unittest import mock

import pytest

from md2wx import drafts
from md2wx.uploader import WeChatApiError


def _resp(payload):
    return io.BytesIO(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def _draft_item(media_id="draft_1", title="示例标题"):
    return {
        "media_id": media_id,
        "update_time": 1700000000,
        "content": {
            "news_item": [{
                "title": title,
                "author": "作者",
                "digest": "摘要",
                "url": "https://mp.weixin.qq.com/s/x",
            }]
        },
    }


class TestDraftApi:

    def test_list_drafts_direct_and_normalize(self):
        responses = [_resp({"total_count": 2, "item_count": 1, "item": [_draft_item()]})]
        captured = []

        def fake_urlopen(req, timeout=30):
            captured.append(req)
            return responses.pop(0)

        with mock.patch("md2wx.drafts.load_env", return_value={}), \
             mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = drafts.list_drafts("tok", count=5)

        assert result["total_count"] == 2
        assert result["items"][0]["title"] == "示例标题"
        assert result["items"][0]["author"] == "作者"
        assert result["items"][0]["url"] == "https://mp.weixin.qq.com/s/x"

        req = captured[0]
        assert "draft/batchget?access_token=tok" in req.full_url
        body = json.loads(req.data.decode("utf-8"))
        assert body == {"offset": 0, "count": 5, "no_content": 0}

    def test_list_drafts_count_clamped_to_wechat_limit(self):
        captured = []

        def fake_urlopen(req, timeout=30):
            captured.append(req)
            return _resp({"total_count": 0, "item_count": 0, "item": []})

        with mock.patch("md2wx.drafts.load_env", return_value={}), \
             mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            drafts.list_drafts("tok", count=99)

        body = json.loads(captured[0].data.decode("utf-8"))
        assert body["count"] == drafts.DRAFT_PAGE_LIMIT

    def test_list_drafts_via_proxy(self):
        captured = []

        def fake_urlopen(req, timeout=30):
            captured.append(req)
            return _resp({"total_count": 0, "item_count": 0, "item": []})

        with mock.patch("md2wx.drafts.load_env", return_value={"WECHAT_PROXY_URL": "https://proxy.example.com"}), \
             mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            drafts.list_drafts("tok")

        req = captured[0]
        assert req.full_url == "https://proxy.example.com"
        body = json.loads(req.data.decode("utf-8"))
        assert body["action"] == "draft_batchget"
        assert body["token"] == "tok"
        assert body["payload"]["no_content"] == 0

    def test_update_draft_payload_shape(self):
        captured = []

        def fake_urlopen(req, timeout=30):
            captured.append(req)
            return _resp({"errcode": 0, "errmsg": "ok"})

        article = {"title": "新标题", "content": "<p>x</p>"}
        with mock.patch("md2wx.drafts.load_env", return_value={}), \
             mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            res = drafts.update_draft("tok", "draft_1", article, index=0)

        assert res["media_id"] == "draft_1"
        req = captured[0]
        assert "draft/update?access_token=tok" in req.full_url
        body = json.loads(req.data.decode("utf-8"))
        assert body["media_id"] == "draft_1"
        assert body["index"] == 0
        # draft/update 的 articles 是单个对象，不是数组
        assert body["articles"] == article

    def test_update_draft_via_proxy_keeps_top_level_media_id(self):
        captured = []

        def fake_urlopen(req, timeout=30):
            captured.append(req)
            return _resp({"errcode": 0})

        with mock.patch("md2wx.drafts.load_env", return_value={"WECHAT_PROXY_URL": "https://proxy.example.com"}), \
             mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            drafts.update_draft("tok", "draft_9", {"title": "t"})

        body = json.loads(captured[0].data.decode("utf-8"))
        assert body["action"] == "draft_update"
        assert body["mediaId"] == "draft_9"
        assert body["payload"]["media_id"] == "draft_9"

    def test_delete_draft(self):
        captured = []

        def fake_urlopen(req, timeout=30):
            captured.append(req)
            return _resp({"errcode": 0})

        with mock.patch("md2wx.drafts.load_env", return_value={}), \
             mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            drafts.delete_draft("tok", "draft_1")

        assert "draft/delete?access_token=tok" in captured[0].full_url
        body = json.loads(captured[0].data.decode("utf-8"))
        assert body == {"media_id": "draft_1"}

    def test_token_expired_retries_with_refresher(self):
        responses = [
            _resp({"errcode": 40001, "errmsg": "invalid credential"}),
            _resp({"errcode": 0}),
        ]
        tokens = []

        def fake_urlopen(req, timeout=30):
            tokens.append(req.full_url)
            return responses.pop(0)

        refresh_calls = []

        def refresher():
            refresh_calls.append(True)
            return "fresh_token"

        with mock.patch("md2wx.drafts.load_env", return_value={}), \
             mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            drafts.delete_draft("stale", "draft_1", token_refresher=refresher)

        assert len(refresh_calls) == 1
        assert "access_token=stale" in tokens[0]
        assert "access_token=fresh_token" in tokens[1]

    def test_proxy_error_field_raises(self):
        """代理网关不支持某动作时返回 {"error": ...}，不能当成空结果吞掉"""
        with mock.patch("md2wx.drafts.load_env", return_value={"WECHAT_PROXY_URL": "https://proxy.example.com"}), \
             mock.patch("urllib.request.urlopen", return_value=_resp({"error": "未知的代理动作: draft_batchget"})):
            with pytest.raises(WeChatApiError) as ctx:
                drafts.list_drafts("tok")

        assert "未知的代理动作" in str(ctx.value)

    def test_non_token_error_not_retried(self):
        refresh_calls = []

        def fake_urlopen(req, timeout=30):
            return _resp({"errcode": 40007, "errmsg": "invalid media_id"})

        with mock.patch("md2wx.drafts.load_env", return_value={}), \
             mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with pytest.raises(WeChatApiError) as ctx:
                drafts.delete_draft("tok", "gone", token_refresher=lambda: refresh_calls.append(True) or "new")

        assert ctx.value.errcode == 40007
        assert refresh_calls == []


class TestDraftState:

    @pytest.fixture(autouse=True)
    def state_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(drafts, "DRAFT_STATE_PATH", tmp_path / "drafts.json")

    def test_file_key_is_absolute(self):
        key = drafts.draft_state_key("relative/post.md", "标题")
        assert key == "file:" + str(Path("relative/post.md").resolve())

    def test_stdin_key_uses_title(self):
        assert drafts.draft_state_key(None, " 我的文章 ") == "title:我的文章"
        assert drafts.draft_state_key(None, "  ") is None

    def test_record_get_and_list(self):
        key = drafts.draft_state_key("/tmp/post.md")
        drafts.record_last_draft(key, "draft_abc", "文章")
        entry = drafts.get_last_draft(key)
        assert entry["media_id"] == "draft_abc"
        assert entry["title"] == "文章"
        assert entry["updated_at"] > 0

        mapping = drafts.list_local_mappings()
        assert mapping["draft_abc"]["key"] == key

    def test_forget_draft_clears_all_matching_keys(self):
        drafts.record_last_draft(drafts.draft_state_key("/tmp/a.md"), "draft_same", "A")
        drafts.record_last_draft(drafts.draft_state_key("/tmp/b.md"), "draft_same", "B")
        drafts.record_last_draft(drafts.draft_state_key("/tmp/c.md"), "draft_other", "C")

        removed = drafts.forget_draft("draft_same")

        assert removed == 2
        assert drafts.get_last_draft(drafts.draft_state_key("/tmp/a.md")) is None
        assert drafts.get_last_draft(drafts.draft_state_key("/tmp/c.md"))["media_id"] == "draft_other"

    def test_forget_key(self):
        key = drafts.draft_state_key("/tmp/post.md")
        drafts.record_last_draft(key, "draft_abc", "文章")
        drafts.forget_key(key)
        assert drafts.get_last_draft(key) is None

    def test_corrupted_state_file_is_ignored(self):
        drafts.DRAFT_STATE_PATH.write_text("not json", encoding="utf-8")
        assert drafts.get_last_draft("file:/x") is None
        drafts.record_last_draft("file:/x", "draft_1", "t")
        assert drafts.get_last_draft("file:/x")["media_id"] == "draft_1"

    def test_missing_media_id_not_recorded(self):
        key = drafts.draft_state_key("/tmp/post.md")
        drafts.record_last_draft(key, "", "文章")
        assert drafts.get_last_draft(key) is None
