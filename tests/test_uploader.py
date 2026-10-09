"""MD2WX 微信素材上传模块单元测试 (Mock 网络请求)"""
import json
from unittest.mock import MagicMock, patch

import pytest

from md2wx import uploader


def _mock_urlopen_response(payload: dict):
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_build_multipart_body_bytes_structure():
    body = uploader._build_multipart_body_bytes(b"IMGDATA", "img.png", "image/png")
    text = body.decode("utf-8", errors="replace")
    assert 'name="media"; filename="img.png"' in text
    assert "Content-Type: image/png" in text
    assert body.endswith(b"\r\n--" + uploader._UPLOAD_BOUNDARY.encode() + b"--\r\n")
    assert b"IMGDATA" in body


def test_build_multipart_body_bytes_escapes_filename():
    body = uploader._build_multipart_body_bytes(b"x", 'evil"\\名字.png', "image/png")
    header = body.split(b"\r\n\r\n")[0].decode("utf-8")
    assert '"' not in header.split('filename="')[1].split('"')[0] or "%22" in header


def test_upload_image_bytes_to_wechat_cdn_success():
    with patch("md2wx.uploader.urllib.request.urlopen") as mock_open, patch(
        "md2wx.uploader._get_proxy_url", return_value=None
    ):
        mock_open.return_value = _mock_urlopen_response({"url": "http://mmbiz.qpic.cn/abc"})
        url = uploader.upload_image_bytes_to_wechat_cdn("TOKEN", b"IMG", "a.png", "image/png")
        assert url == "http://mmbiz.qpic.cn/abc"
        req = mock_open.call_args[0][0]
        assert "uploadimg" in req.full_url


def test_upload_image_bytes_to_wechat_cdn_error_payload():
    with patch("md2wx.uploader.urllib.request.urlopen") as mock_open, patch(
        "md2wx.uploader._get_proxy_url", return_value=None
    ):
        mock_open.return_value = _mock_urlopen_response({"errcode": 40007, "errmsg": "invalid media"})
        with pytest.raises(RuntimeError, match="invalid media"):
            uploader.upload_image_bytes_to_wechat_cdn("TOKEN", b"IMG", "a.png")


def test_upload_image_bytes_proxy_payload():
    """代理模式下走 WECHAT_PROXY_URL 并在 multipart 中附带 action=uploadimg"""
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["req"] = req
        return _mock_urlopen_response({"url": "http://mmbiz.qpic.cn/x"})

    with patch("md2wx.uploader.urllib.request.urlopen", side_effect=fake_urlopen), patch(
        "md2wx.uploader._get_proxy_url", return_value="https://proxy.example.com/wx"
    ):
        url = uploader.upload_image_bytes_to_wechat_cdn("TOKEN", b"IMG", "a.png", "image/png")
        assert url == "http://mmbiz.qpic.cn/x"
        body = captured["req"].data.decode("utf-8", errors="replace")
        assert "uploadimg" in body
        assert "TOKEN" in body


def test_get_access_token_success_and_failure():
    with patch("md2wx.uploader.urllib.request.urlopen") as mock_open, patch(
        "md2wx.uploader._get_proxy_url", return_value=None
    ):
        mock_open.return_value = _mock_urlopen_response({"access_token": "AT", "expires_in": 7200})
        assert uploader.get_access_token("id", "secret") == "AT"

    with patch("md2wx.uploader.urllib.request.urlopen") as mock_open, patch(
        "md2wx.uploader._get_proxy_url", return_value=None
    ):
        mock_open.return_value = _mock_urlopen_response({"errcode": 40013, "errmsg": "invalid appid"})
        with pytest.raises(RuntimeError, match="invalid appid"):
            uploader.get_access_token("id", "secret")


def test_upload_cover_material_md5_cache(tmp_path, monkeypatch):
    """相同内容图片命中 md5 缓存时不重复发起上传请求"""
    cache_file = tmp_path / "material_cache.json"
    monkeypatch.setattr(uploader, "MATERIAL_CACHE_PATH", cache_file)

    img = tmp_path / "cover.png"
    img.write_bytes(b"COVERBYTES")

    calls = []

    def fake_urlopen(req, timeout=0):
        calls.append(req)
        return _mock_urlopen_response({"media_id": "MEDIA_1"})

    with patch("md2wx.uploader.urllib.request.urlopen", side_effect=fake_urlopen), patch(
        "md2wx.uploader._get_proxy_url", return_value=None
    ):
        first = uploader.upload_cover_material("TOKEN", str(img))
        second = uploader.upload_cover_material("TOKEN", str(img))

    assert first == second == "MEDIA_1"
    assert len(calls) == 1  # 第二次命中缓存


def test_upload_cover_material_missing_file():
    with pytest.raises(OSError):
        uploader.upload_cover_material("TOKEN", "/nonexistent/cover.png")
