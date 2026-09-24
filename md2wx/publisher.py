"""
MD2WX 微信公众平台草稿箱发布服务
"""
import json
import urllib.request
from typing import Dict, Any, Optional
from .uploader import upload_cover_material
from .envutil import load_env

def publish_draft_to_wechat(
    token: str,
    title: str,
    content_html: str,
    author: str = "野生宝藏箱",
    digest: str = "",
    thumb_media_id: Optional[str] = None,
    cover_image_path: Optional[str] = None,
    pic_crop_235_1: Optional[str] = None,
    pic_crop_1_1: Optional[str] = None,
    content_source_url: str = ""
) -> Dict[str, Any]:
    """
    提交文章到微信公众号草稿箱 (draft/add)
    支持传入 pic_crop_235_1 与 pic_crop_1_1 精确设定微信头条与次条/会话方图的裁切坐标
    """
    # 1. 如果未直接提供 thumb_media_id，尝试上传封面图
    if not thumb_media_id and cover_image_path:
        thumb_media_id = upload_cover_material(token, cover_image_path)

    if not thumb_media_id:
        raise ValueError("微信公众号图文草稿必须指定封面图 (需提供 thumb_media_id 或有效的 cover_image_path)")

    article_obj = {
        "title": title,
        "author": author,
        "digest": digest,
        "content": content_html,
        "content_source_url": content_source_url,
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 1,
        "only_fans_can_comment": 0
    }
    if pic_crop_235_1:
        article_obj["pic_crop_235_1"] = pic_crop_235_1
    if pic_crop_1_1:
        article_obj["pic_crop_1_1"] = pic_crop_1_1

    payload = {
        "articles": [article_obj]
    }

    proxy_url = load_env().get("WECHAT_PROXY_URL")
    if proxy_url and proxy_url.strip():
        proxy_url = proxy_url.strip()
        req = urllib.request.Request(
            proxy_url,
            data=json.dumps({"action": "draft", "token": token, "payload": payload}, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
            }
        )
        res_raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
        res = json.loads(res_raw)
        draft_media_id = res.get("media_id")
        if res.get("errcode") or not draft_media_id:
            raise RuntimeError(f"微信草稿提交失败: {res.get('errmsg', res)}")

        preview_url = ""
        try:
            verify_req = urllib.request.Request(
                proxy_url,
                data=json.dumps({"action": "draft_get", "token": token, "mediaId": draft_media_id}).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                }
            )
            verify_res = json.loads(urllib.request.urlopen(verify_req, timeout=15).read().decode("utf-8"))
            news_items = verify_res.get("news_item", [])
            if news_items:
                preview_url = news_items[0].get("url", "")
        except Exception:
            pass

        return {
            "media_id": draft_media_id,
            "preview_url": preview_url,
            "title": title,
            "author": author,
            "thumb_media_id": thumb_media_id,
            "pic_crop_235_1": pic_crop_235_1,
            "pic_crop_1_1": pic_crop_1_1
        }

    req = urllib.request.Request(
        f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"}
    )

    res_raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    res = json.loads(res_raw)
    draft_media_id = res.get("media_id")
    if res.get("errcode") or not draft_media_id:
        raise RuntimeError(f"微信草稿提交失败: {res.get('errmsg', res)}")

    # 2. 尝试读取草稿详情获取微信官方临时预览 URL
    preview_url = ""
    try:
        verify_req = urllib.request.Request(
            f"https://api.weixin.qq.com/cgi-bin/draft/get?access_token={token}",
            data=json.dumps({"media_id": draft_media_id}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        verify_res = json.loads(urllib.request.urlopen(verify_req, timeout=15).read().decode("utf-8"))
        news_items = verify_res.get("news_item", [])
        if news_items:
            preview_url = news_items[0].get("url", "")
    except Exception:
        pass

    return {
        "media_id": draft_media_id,
        "preview_url": preview_url,
        "title": title,
        "author": author,
        "thumb_media_id": thumb_media_id,
        "pic_crop_235_1": pic_crop_235_1,
        "pic_crop_1_1": pic_crop_1_1
    }
