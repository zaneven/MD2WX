"""
MD2WX 微信公众平台素材与图片管理
"""
import os
import json
import time
import hashlib
import mimetypes
import urllib.request
from urllib.parse import quote as url_quote
from pathlib import Path
from typing import Dict, Optional
from .envutil import load_env

# 永久素材本地缓存：按文件内容 md5 记录 media_id，避免重复上传消耗配额
MATERIAL_CACHE_PATH = Path.home() / ".config" / "md2wx" / "material_cache.json"
# access_token 本地缓存：按 app_id 记录凭据与过期时间，避免频繁调用 token 接口撞微信频控
TOKEN_CACHE_PATH = Path.home() / ".config" / "md2wx" / "token_cache.json"
# 判定 token 过期时预留的安全余量 (秒)：微信 token 有效期 7200s，提前 5 分钟视为失效
TOKEN_EXPIRY_MARGIN = 300
# token 失效类错误码：凭据非法 (40001)、过期 (42001)、非法 (40014)
TOKEN_EXPIRED_ERRCODES = (40001, 42001, 40014)


class WeChatApiError(RuntimeError):
    """微信 API 业务错误：携带官方 errcode，供调用方按错误码分流 (如 token 失效重试)"""

    def __init__(self, message: str, errcode: Optional[int] = None):
        super().__init__(message)
        self.errcode = errcode

def _get_proxy_url() -> Optional[str]:
    proxy = load_env().get("WECHAT_PROXY_URL")
    return proxy.strip() if proxy and proxy.strip() else None

def _proxy_headers(content_type: str) -> dict:
    return {
        "Content-Type": content_type,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    }

def _load_material_cache() -> Dict[str, str]:
    try:
        with open(MATERIAL_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _save_material_cache(cache: Dict[str, str]) -> None:
    try:
        MATERIAL_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MATERIAL_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 缓存写失败不影响主流程

def _load_token_cache() -> Dict[str, dict]:
    try:
        with open(TOKEN_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _save_token_cache(cache: Dict[str, dict]) -> None:
    try:
        TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 缓存写失败不影响主流程

def _fetch_access_token(app_id: str, app_secret: str) -> dict:
    """调用微信 token 接口取新凭据，返回含 access_token 与 expires_in 的原始响应"""
    proxy_url = _get_proxy_url()
    if proxy_url:
        payload = json.dumps({"action": "token", "appId": app_id, "appSecret": app_secret}).encode("utf-8")
        req = urllib.request.Request(proxy_url, data=payload, headers=_proxy_headers("application/json"))
        res = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
        if "access_token" not in res:
            raise WeChatApiError(
                f"获取微信 Access Token 失败 (via proxy): {res.get('errmsg', res)}",
                errcode=res.get("errcode"),
            )
        return res

    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    req = urllib.request.urlopen(url, timeout=15)
    res = json.loads(req.read().decode("utf-8"))
    if "access_token" not in res:
        raise WeChatApiError(
            f"获取微信 Access Token 失败: {res.get('errmsg', res)}",
            errcode=res.get("errcode"),
        )
    return res

def get_access_token(app_id: str, app_secret: str, force_refresh: bool = False) -> str:
    """
    获取微信公众平台全局唯一后台接口调用凭据 (access_token)
    默认读取本地缓存 (按 app_id 隔离)，未过期则直接复用，避免频繁请求撞微信频控；
    force_refresh=True 时无视缓存强制取新 (用于 40001/42001 失效重试)
    """
    if not force_refresh:
        cache = _load_token_cache()
        entry = cache.get(app_id)
        if isinstance(entry, dict) and entry.get("token"):
            # 预留安全余量：距过期不足 5 分钟即视为失效
            if time.time() < float(entry.get("expires_at", 0)) - TOKEN_EXPIRY_MARGIN:
                return entry["token"]

    res = _fetch_access_token(app_id, app_secret)
    expires_in = int(res.get("expires_in", 7200) or 7200)
    cache = _load_token_cache()
    cache[app_id] = {
        "token": res["access_token"],
        "expires_at": time.time() + expires_in,
    }
    _save_token_cache(cache)
    return res["access_token"]

_UPLOAD_BOUNDARY = "----WebKitFormBoundaryMD2WXUpload"

def _build_multipart_body_bytes(file_bytes: bytes, filename: str, mime_type: str, field: str = "media") -> bytes:
    """构造 multipart/form-data 请求体，filename 安全转义；field 默认为微信素材接口的 media"""
    # 转义引号与反斜杠，并百分号编码非 ASCII 字符，避免破坏 multipart 头
    safe_name = url_quote(filename.replace("\\", "").replace('"', ""), safe="()<>@,;:\\\"/[]?={}")
    return (
        f"--{_UPLOAD_BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{safe_name}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{_UPLOAD_BOUNDARY}--\r\n".encode("utf-8")

def _build_multipart_body(filepath: str) -> bytes:
    """构造 multipart/form-data 请求体，MIME 类型按扩展名推断"""
    filename = os.path.basename(filepath)
    mime_type = mimetypes.guess_type(filename)[0] or "image/png"
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    return _build_multipart_body_bytes(file_bytes, filename, mime_type)

def upload_image_bytes_to_wechat_cdn(token: str, file_bytes: bytes, filename: str = "image.png", mime_type: Optional[str] = None) -> str:
    """
    上传图文消息内的图片字节获取微信官方 CDN URL (http://mmbiz.qpic.cn/...)
    支持本地文件、外链下载字节、Base64 解码字节，用于发布前统一换链。
    """
    mime = mime_type or mimetypes.guess_type(filename)[0] or "image/png"
    proxy_url = _get_proxy_url()
    if proxy_url:
        safe_name = url_quote(filename.replace("\\", "").replace('"', ""), safe="()<>@,;:\\\"/[]?={}")
        body = (
            f"--{_UPLOAD_BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="action"\r\n\r\n'
            f"uploadimg\r\n"
            f"--{_UPLOAD_BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="token"\r\n\r\n'
            f"{token}\r\n"
            f"--{_UPLOAD_BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="media"; filename="{safe_name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{_UPLOAD_BOUNDARY}--\r\n".encode("utf-8")
        req = urllib.request.Request(
            proxy_url,
            data=body,
            headers=_proxy_headers(f"multipart/form-data; boundary={_UPLOAD_BOUNDARY}")
        )
        res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
        if "url" not in res:
            raise RuntimeError(f"正文图片上传微信失败 ({filename}): {res.get('errmsg', res)}")
        return res["url"]

    req = urllib.request.Request(
        f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}",
        data=_build_multipart_body_bytes(file_bytes, filename, mime),
        headers={"Content-Type": f"multipart/form-data; boundary={_UPLOAD_BOUNDARY}"}
    )
    res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    if "url" not in res:
        raise RuntimeError(f"正文图片上传微信失败 ({filename}): {res.get('errmsg', res)}")
    return res["url"]

def upload_image_to_wechat_cdn(token: str, filepath: str) -> str:
    """
    上传图文消息内的图片获取微信官方 CDN URL (http://mmbiz.qpic.cn/...)
    此接口不占用公众号永久素材库数量限制。
    """
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    return upload_image_bytes_to_wechat_cdn(token, file_bytes, filename)

def upload_cover_material(token: str, filepath: str) -> str:
    """
    上传永久图片素材，用于获取草稿箱封面图所需的 thumb_media_id
    相同内容 (md5 一致) 的图片会复用本地缓存的 media_id，不重复消耗永久素材配额
    """
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    content_md5 = hashlib.md5(file_bytes).hexdigest()

    cache = _load_material_cache()
    if content_md5 in cache:
        return cache[content_md5]

    proxy_url = _get_proxy_url()
    filename = os.path.basename(filepath)
    mime = mimetypes.guess_type(filename)[0] or "image/png"

    if proxy_url:
        safe_name = url_quote(filename.replace("\\", "").replace('"', ""), safe="()<>@,;:\\\"/[]?={}")
        body = (
            f"--{_UPLOAD_BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="action"\r\n\r\n'
            f"material\r\n"
            f"--{_UPLOAD_BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="token"\r\n\r\n'
            f"{token}\r\n"
            f"--{_UPLOAD_BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="media"; filename="{safe_name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{_UPLOAD_BOUNDARY}--\r\n".encode("utf-8")
        req = urllib.request.Request(
            proxy_url,
            data=body,
            headers=_proxy_headers(f"multipart/form-data; boundary={_UPLOAD_BOUNDARY}")
        )
        res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
        if "media_id" not in res:
            raise WeChatApiError(
                f"封面素材上传微信失败 ({filename}): {res.get('errmsg', res)}",
                errcode=res.get("errcode"),
            )
        cache[content_md5] = res["media_id"]
        _save_material_cache(cache)
        return res["media_id"]

    req = urllib.request.Request(
        f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image",
        data=_build_multipart_body(filepath),
        headers={"Content-Type": f"multipart/form-data; boundary={_UPLOAD_BOUNDARY}"}
    )
    res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    if "media_id" not in res:
        raise WeChatApiError(
            f"封面素材上传微信失败 ({os.path.basename(filepath)}): {res.get('errmsg', res)}",
            errcode=res.get("errcode"),
        )

    cache[content_md5] = res["media_id"]
    _save_material_cache(cache)
    return res["media_id"]
