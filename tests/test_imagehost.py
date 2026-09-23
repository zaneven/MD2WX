"""
MD2WX 在线图床客户端单元测试 (零第三方依赖)
"""
import json
import os
import sys
import unittest
from io import BytesIO
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from md2wx import imagehost
from md2wx.imagehost import (
    ImageHostConfig,
    _build_multipart_body,
    _extract_by_path,
    download_image_bytes,
    get_image_host_config,
    is_image_host_configured,
    upload_image_bytes,
)
from md2wx import envutil


class _FakeResp:
    """模拟 urllib urlopen 上下文管理器"""

    def __init__(self, payload=b"", status=200, headers=None, content_type="application/json"):
        self._payload = payload if isinstance(payload, bytes) else payload.encode("utf-8")
        self.status = status
        self.headers = headers or {"Content-Type": content_type}

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TestImageHostConfig(unittest.TestCase):
    def test_unconfigured_returns_none(self):
        self.assertIsNone(get_image_host_config({}))
        self.assertFalse(is_image_host_configured({}))
        self.assertIsNone(get_image_host_config({"IMAGE_HOST_UPLOAD_URL": "your_image_host_upload_url_here"}))
        self.assertIsNone(get_image_host_config({"IMAGE_HOST_UPLOAD_URL": "ftp://x.example.com"}))

    def test_configured_parses_fields(self):
        cfg = get_image_host_config({
            "IMAGE_HOST_UPLOAD_URL": "https://img.example.com/api/uploads",
            "IMAGE_HOST_TOKEN": "tok123",
            "IMAGE_HOST_FILE_FIELD": "image",
            "IMAGE_HOST_RESPONSE_PATH": "data.link",
            "IMAGE_HOST_TIMEOUT": "12",
        })
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.upload_url, "https://img.example.com/api/uploads")
        self.assertEqual(cfg.token, "tok123")
        self.assertEqual(cfg.file_field, "image")
        self.assertEqual(cfg.response_path, "data.link")
        self.assertEqual(cfg.timeout, 12)
        self.assertTrue(is_image_host_configured({
            "IMAGE_HOST_UPLOAD_URL": "https://img.example.com/api/uploads"
        }))


class TestExtractByPath(unittest.TestCase):
    def test_simple_key(self):
        self.assertEqual(_extract_by_path({"url": "http://a.b/c.png"}, "url"), "http://a.b/c.png")

    def test_nested_dotted(self):
        self.assertEqual(_extract_by_path({"data": {"link": "http://a.b/c"}}, "data.link"), "http://a.b/c")

    def test_list_index(self):
        self.assertEqual(_extract_by_path({"items": [{"url": "u1"}]}, "items.0.url"), "u1")

    def test_missing_returns_none(self):
        self.assertIsNone(_extract_by_path({"a": 1}, "b"))
        self.assertIsNone(_extract_by_path({}, "url"))

    def test_non_string_returns_none(self):
        self.assertIsNone(_extract_by_path({"url": 123}, "url"))


class TestMultipartBody(unittest.TestCase):
    def test_body_contains_field_and_filename(self):
        body = _build_multipart_body(
            fields=[("key", "value")],
            filename="test.png",
            mime_type="image/png",
            file_bytes=b"\x89PNG\r\n",
            file_field="file",
        )
        text = body.decode("utf-8", errors="replace")
        self.assertIn('name="key"', text)
        self.assertIn('filename="test.png"', text)
        self.assertIn("Content-Type: image/png", text)
        self.assertIn("value", text)
        self.assertTrue(body.endswith(b"--\r\n") or b"--\r\n" in body)


class TestUploadImageBytes(unittest.TestCase):
    def test_missing_config_raises(self):
        with mock.patch.object(imagehost, "get_image_host_config", return_value=None):
            with self.assertRaises(RuntimeError):
                upload_image_bytes(b"data", "a.png")

    def test_success_returns_url(self):
        cfg = ImageHostConfig("https://img.example.com/api/uploads", response_path="url")
        payload = json.dumps({"url": "https://cdn.example.com/x.png"}).encode("utf-8")
        with mock.patch.object(imagehost, "get_image_host_config", return_value=cfg):
            with mock.patch("urllib.request.urlopen", return_value=_FakeResp(payload)):
                url = upload_image_bytes(b"\x89PNG", "x.png", "image/png", cfg)
        self.assertEqual(url, "https://cdn.example.com/x.png")

    def test_token_as_header(self):
        cfg = ImageHostConfig("https://img.example.com/api/uploads", token="tok123", auth_prefix="Bearer ")
        captured = {}

        def fake_urlopen(req, timeout=30):
            captured["header"] = req.headers.get("Authorization")
            return _FakeResp(json.dumps({"url": "https://cdn.example.com/y.png"}).encode("utf-8"))

        with mock.patch.object(imagehost, "get_image_host_config", return_value=cfg):
            with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                url = upload_image_bytes(b"\x89PNG", "y.png", "image/png", cfg)
        self.assertEqual(url, "https://cdn.example.com/y.png")
        self.assertEqual(captured["header"], "Bearer tok123")

    def test_token_as_field(self):
        cfg = ImageHostConfig("https://img.example.com/api/uploads", token="tok123", token_field="key")
        captured = {}

        def fake_urlopen(req, timeout=30):
            captured["body"] = req.data.decode("utf-8", errors="replace")
            self.assertNotIn("Authorization", req.headers)
            return _FakeResp(json.dumps({"url": "https://cdn.example.com/z.png"}).encode("utf-8"))

        with mock.patch.object(imagehost, "get_image_host_config", return_value=cfg):
            with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                url = upload_image_bytes(b"\x89PNG", "z.png", "image/png", cfg)
        self.assertEqual(url, "https://cdn.example.com/z.png")
        self.assertIn('name="key"', captured["body"])

    def test_response_path_missing_raises(self):
        cfg = ImageHostConfig("https://img.example.com/api/uploads", response_path="data.url")
        payload = json.dumps({"data": {}}).encode("utf-8")
        with mock.patch.object(imagehost, "get_image_host_config", return_value=cfg):
            with mock.patch("urllib.request.urlopen", return_value=_FakeResp(payload)):
                with self.assertRaises(RuntimeError):
                    upload_image_bytes(b"\x89PNG", "x.png", "image/png", cfg)


class TestDownloadImageBytes(unittest.TestCase):
    def test_invalid_scheme_raises(self):
        with self.assertRaises(ValueError):
            download_image_bytes("ftp://x.example.com/a.png")

    def test_success(self):
        resp = _FakeResp(b"\x89PNG\r\n", content_type="image/png")
        resp.headers = {"Content-Type": "image/png"}
        with mock.patch("urllib.request.urlopen", return_value=resp):
            data, filename, mime = download_image_bytes("https://cdn.example.com/path/photo.png")
        self.assertEqual(data, b"\x89PNG\r\n")
        self.assertEqual(filename, "photo.png")
        self.assertEqual(mime, "image/png")

    def test_filename_fallback_from_mime(self):
        resp = _FakeResp(b"\x89PNG\r\n")
        resp.headers = {"Content-Type": "image/png"}
        with mock.patch("urllib.request.urlopen", return_value=resp):
            data, filename, mime = download_image_bytes("https://cdn.example.com/noext")
        self.assertEqual(data, b"\x89PNG\r\n")
        self.assertTrue(filename.endswith(".png"))
        self.assertEqual(mime, "image/png")


class TestEnvUtil(unittest.TestCase):
    def test_is_placeholder(self):
        self.assertTrue(envutil.is_placeholder(""))
        self.assertTrue(envutil.is_placeholder("  "))
        self.assertTrue(envutil.is_placeholder("your_value"))
        self.assertTrue(envutil.is_placeholder("<placeholder>"))
        self.assertFalse(envutil.is_placeholder("real_token"))

    def test_parse_env_line_skips_placeholder(self):
        env = {"UPLOAD_URL": "https://x.example.com/api", "TOKEN": "your_token"}
        # read_env_file 用不到，直接验证 is_placeholder 过滤逻辑
        self.assertTrue(envutil.is_placeholder(env["TOKEN"]))
        self.assertFalse(envutil.is_placeholder(env["UPLOAD_URL"]))


if __name__ == "__main__":
    unittest.main()
