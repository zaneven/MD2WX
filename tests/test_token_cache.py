"""
access_token 本地缓存单元测试
验证按 app_id 隔离的凭据缓存、过期判定与 force_refresh 强制刷新链路
"""
import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from md2wx import uploader


class TestAccessTokenCache(unittest.TestCase):

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        cache_path = Path(self._tmp.name) / "token_cache.json"
        patcher = mock.patch.object(uploader, "TOKEN_CACHE_PATH", cache_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_token_cached_and_reused(self):
        """第二次调用命中缓存，不再请求微信接口"""
        with mock.patch.object(
            uploader, "_fetch_access_token",
            return_value={"access_token": "TOKEN_A", "expires_in": 7200},
        ) as fetch:
            t1 = uploader.get_access_token("appid_1", "secret")
            t2 = uploader.get_access_token("appid_1", "secret")

        self.assertEqual(t1, "TOKEN_A")
        self.assertEqual(t2, "TOKEN_A")
        self.assertEqual(fetch.call_count, 1)

    def test_token_cache_isolated_by_app_id(self):
        """不同 app_id 的凭据互不串用"""
        def fake_fetch(app_id, app_secret):
            return {"access_token": f"TOKEN_{app_id}", "expires_in": 7200}

        with mock.patch.object(uploader, "_fetch_access_token", side_effect=fake_fetch):
            t1 = uploader.get_access_token("appid_1", "secret")
            t2 = uploader.get_access_token("appid_2", "secret")

        self.assertEqual(t1, "TOKEN_appid_1")
        self.assertEqual(t2, "TOKEN_appid_2")

    def test_expired_token_triggers_refetch(self):
        """缓存条目已过安全余量期时重新取凭据"""
        cache = {
            "appid_1": {
                "token": "TOKEN_STALE",
                "expires_at": time.time() - 1,  # 已过期
            }
        }
        with open(uploader.TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f)

        with mock.patch.object(
            uploader, "_fetch_access_token",
            return_value={"access_token": "TOKEN_NEW", "expires_in": 7200},
        ) as fetch:
            t = uploader.get_access_token("appid_1", "secret")

        self.assertEqual(t, "TOKEN_NEW")
        self.assertEqual(fetch.call_count, 1)

    def test_near_expiry_within_margin_refetches(self):
        """距过期不足安全余量 (5 分钟) 即视为失效，触发重新获取"""
        cache = {
            "appid_1": {
                "token": "TOKEN_ALMOST_DEAD",
                "expires_at": time.time() + uploader.TOKEN_EXPIRY_MARGIN - 60,
            }
        }
        with open(uploader.TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f)

        with mock.patch.object(
            uploader, "_fetch_access_token",
            return_value={"access_token": "TOKEN_REFRESHED", "expires_in": 7200},
        ):
            t = uploader.get_access_token("appid_1", "secret")

        self.assertEqual(t, "TOKEN_REFRESHED")

    def test_force_refresh_bypasses_valid_cache(self):
        """force_refresh=True 无视未过期缓存强制取新 (40001 重试链路依赖此行为)"""
        cache = {
            "appid_1": {
                "token": "TOKEN_VALID",
                "expires_at": time.time() + 3600,
            }
        }
        with open(uploader.TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f)

        with mock.patch.object(
            uploader, "_fetch_access_token",
            return_value={"access_token": "TOKEN_FORCED", "expires_in": 7200},
        ) as fetch:
            t = uploader.get_access_token("appid_1", "secret", force_refresh=True)

        self.assertEqual(t, "TOKEN_FORCED")
        self.assertEqual(fetch.call_count, 1)

    def test_corrupted_cache_file_falls_back_to_fetch(self):
        """缓存文件损坏时不抛异常，回退到正常取凭据"""
        with open(uploader.TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
            f.write("not valid json {{{")

        with mock.patch.object(
            uploader, "_fetch_access_token",
            return_value={"access_token": "TOKEN_FALLBACK", "expires_in": 7200},
        ):
            t = uploader.get_access_token("appid_1", "secret")

        self.assertEqual(t, "TOKEN_FALLBACK")


if __name__ == "__main__":
    unittest.main()
