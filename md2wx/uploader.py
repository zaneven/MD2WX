"""
MD2WX 微信公众平台素材与图片管理
"""
import os
import json
import hashlib
import mimetypes
import urllib.request
from urllib.parse import quote as url_quote
from pathlib import Path
from typing import Dict, Optional

# 永久素材本地缓存：按文件内容 md5 记录 media_id，避免重复上传消耗配额
MATERIAL_CACHE_PATH = Path.home() / ".config" / "md2wx" / "material_cache.json"

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

def get_access_token(app_id: str, app_secret: str) -> str:
    """获取微信公众平台全局唯一后台接口调用凭据 (access_token)"""
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    req = urllib.request.urlopen(url, timeout=15)
    res = json.loads(req.read().decode("utf-8"))
    if "access_token" not in res:
        raise RuntimeError(f"获取微信 Access Token 失败: {res.get('errmsg', res)}")
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

    req = urllib.request.Request(
        f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image",
        data=_build_multipart_body(filepath),
        headers={"Content-Type": f"multipart/form-data; boundary={_UPLOAD_BOUNDARY}"}
    )
    res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    if "media_id" not in res:
        raise RuntimeError(f"封面素材上传微信失败 ({os.path.basename(filepath)}): {res.get('errmsg', res)}")

    cache[content_md5] = res["media_id"]
    _save_material_cache(cache)
    return res["media_id"]
