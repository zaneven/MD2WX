"""
MD2WX 微信公众平台素材与图片管理
"""
import os
import json
import urllib.request
from typing import Dict, Optional

def get_access_token(app_id: str, app_secret: str) -> str:
    """获取微信公众平台全局唯一后台接口调用凭据 (access_token)"""
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    req = urllib.request.urlopen(url, timeout=15)
    res = json.loads(req.read().decode("utf-8"))
    if "access_token" not in res:
        raise RuntimeError(f"获取微信 Access Token 失败: {res.get('errmsg', res)}")
    return res["access_token"]

def upload_image_to_wechat_cdn(token: str, filepath: str) -> str:
    """
    上传图文消息内的图片获取微信官方 CDN URL (http://mmbiz.qpic.cn/...)
    此接口不占用公众号永久素材库数量限制。
    """
    boundary = "----WebKitFormBoundaryMD2WXUpload"
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        file_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    if "url" not in res:
        raise RuntimeError(f"正文图片上传微信失败 ({filename}): {res.get('errmsg', res)}")
    return res["url"]

def upload_cover_material(token: str, filepath: str) -> str:
    """
    上传永久图片素材，用于获取草稿箱封面图所需的 thumb_media_id
    """
    boundary = "----WebKitFormBoundaryMD2WXCover"
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        file_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    if "media_id" not in res:
        raise RuntimeError(f"封面素材上传微信失败 ({filename}): {res.get('errmsg', res)}")
    return res["media_id"]
