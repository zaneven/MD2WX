"""
MD2WX 微信草稿箱发布服务单元测试
"""
import io
import json
import unittest
from unittest import mock

from md2wx.publisher import publish_draft_to_wechat


class TestPublisher(unittest.TestCase):

    def test_publish_draft_payload_with_crop_coordinates(self):
        """测试发布草稿时正确注入双比例裁剪坐标 (pic_crop_235_1 与 pic_crop_1_1)"""
        mock_response_data = json.dumps({"media_id": "test_draft_media_id"}).encode("utf-8")
        mock_get_response_data = json.dumps({
            "news_item": [{"url": "https://mp.weixin.qq.com/s/preview_test"}]
        }).encode("utf-8")

        responses = [
            io.BytesIO(mock_response_data),
            io.BytesIO(mock_get_response_data),
        ]

        captured_requests = []

        def mock_urlopen(req, timeout=30):
            captured_requests.append(req)
            return responses.pop(0)

        with mock.patch("md2wx.publisher.load_env", return_value={}), \
             mock.patch("urllib.request.urlopen", side_effect=mock_urlopen):
            res = publish_draft_to_wechat(
                token="test_token",
                title="测试标题",
                content_html="<p>正文内容</p>",
                author="测试作者",
                digest="测试摘要",
                thumb_media_id="test_thumb_123",
                pic_crop_235_1="0_0_0.701493_1",
                pic_crop_1_1="0.701493_0_1_1",
            )

        self.assertEqual(res["media_id"], "test_draft_media_id")
        self.assertEqual(res["preview_url"], "https://mp.weixin.qq.com/s/preview_test")
        self.assertEqual(res["pic_crop_235_1"], "0_0_0.701493_1")
        self.assertEqual(res["pic_crop_1_1"], "0.701493_0_1_1")

        # 校验直接请求微信官方 API 的 payload
        add_req = captured_requests[0]
        self.assertIn("api.weixin.qq.com", add_req.full_url)
        body = json.loads(add_req.data.decode("utf-8"))
        article = body["articles"][0]
        self.assertEqual(article["title"], "测试标题")
        self.assertEqual(article["thumb_media_id"], "test_thumb_123")
        self.assertEqual(article["pic_crop_235_1"], "0_0_0.701493_1")
        self.assertEqual(article["pic_crop_1_1"], "0.701493_0_1_1")

    def test_publish_draft_via_proxy_with_crop_coordinates(self):
        """测试通过代理网关发布草稿时 payload 包含裁剪坐标"""
        mock_response_data = json.dumps({"media_id": "proxy_draft_media_id"}).encode("utf-8")
        mock_get_response_data = json.dumps({
            "news_item": [{"url": "https://mp.weixin.qq.com/s/proxy_preview"}]
        }).encode("utf-8")

        responses = [
            io.BytesIO(mock_response_data),
            io.BytesIO(mock_get_response_data),
        ]

        captured_requests = []

        def mock_urlopen(req, timeout=30):
            captured_requests.append(req)
            return responses.pop(0)

        with mock.patch("md2wx.publisher.load_env", return_value={"WECHAT_PROXY_URL": "https://proxy.example.com"}), \
             mock.patch("urllib.request.urlopen", side_effect=mock_urlopen):
            res = publish_draft_to_wechat(
                token="test_token",
                title="代理标题",
                content_html="<p>正文</p>",
                thumb_media_id="proxy_thumb_456",
                pic_crop_235_1="0_0_0.701493_1",
                pic_crop_1_1="0.701493_0_1_1",
            )

        self.assertEqual(res["media_id"], "proxy_draft_media_id")
        self.assertEqual(res["pic_crop_235_1"], "0_0_0.701493_1")
        self.assertEqual(res["pic_crop_1_1"], "0.701493_0_1_1")

        add_req = captured_requests[0]
        self.assertEqual(add_req.full_url, "https://proxy.example.com")
        body = json.loads(add_req.data.decode("utf-8"))
        article = body["payload"]["articles"][0]
        self.assertEqual(article["pic_crop_235_1"], "0_0_0.701493_1")
        self.assertEqual(article["pic_crop_1_1"], "0.701493_0_1_1")

    def test_publish_draft_without_crop_coordinates(self):
        """测试未指定裁剪坐标时不注入 pic_crop_* 字段"""
        mock_response_data = json.dumps({"media_id": "test_draft_media_id"}).encode("utf-8")
        mock_get_response_data = json.dumps({"news_item": []}).encode("utf-8")

        responses = [
            io.BytesIO(mock_response_data),
            io.BytesIO(mock_get_response_data),
        ]

        captured_requests = []

        def mock_urlopen(req, timeout=30):
            captured_requests.append(req)
            return responses.pop(0)

        with mock.patch("md2wx.publisher.load_env", return_value={}), \
             mock.patch("urllib.request.urlopen", side_effect=mock_urlopen):
            res = publish_draft_to_wechat(
                token="test_token",
                title="测试标题",
                content_html="<p>正文</p>",
                thumb_media_id="test_thumb_123",
            )

        add_req = captured_requests[0]
        body = json.loads(add_req.data.decode("utf-8"))
        article = body["articles"][0]
        self.assertNotIn("pic_crop_235_1", article)
        self.assertNotIn("pic_crop_1_1", article)
        self.assertIsNone(res["pic_crop_235_1"])
        self.assertIsNone(res["pic_crop_1_1"])

    def test_publish_draft_requires_cover(self):
        """测试未指定 thumb_media_id 且未提供封面图路径时抛出 ValueError"""
        with self.assertRaises(ValueError):
            publish_draft_to_wechat(
                token="test_token",
                title="标题",
                content_html="<p>内容</p>",
            )


if __name__ == "__main__":
    unittest.main()
