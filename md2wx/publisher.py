"""
MD2WX 微信公众平台草稿箱发布服务
"""
import json
import urllib.request
from typing import Dict, Any, Optional
from .uploader import upload_cover_material

def publish_draft_to_wechat(
    token: str,
    title: str,
    content_html: str,
    author: str = "野生宝藏箱",
    digest: str = "",
    thumb_media_id: Optional[str] = None,
    cover_image_path: Optional[str] = None,
    content_source_url: str = ""
) -> Dict[str, Any]:
    """
    提交文章到微信公众号草稿箱 (draft/add)
    """
    # 1. 如果未直接提供 thumb_media_id，尝试上传封面图
    if not thumb_media_id and cover_image_path:
        thumb_media_id = upload_cover_material(token, cover_image_path)

    if not thumb_media_id:
        raise ValueError("微信公众号图文草稿必须指定封面图 (需提供 thumb_media_id 或有效的 cover_image_path)")

    payload = {
        "articles": [
            {
                "title": title,
                "author": author,
                "digest": digest,
                "content": content_html,
                "content_source_url": content_source_url,
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 1,
                "only_fans_can_comment": 0
            }
        ]
    }

    req = urllib.request.Request(
        f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"}
    )

    res_raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    res = json.loads(res_raw)
    if res.get("errcode") and res.get("errcode") != 0:
        raise RuntimeError(f"微信草稿提交失败: {res.get('errmsg', res)}")

    draft_media_id = res.get("media_id")

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
        "thumb_media_id": thumb_media_id
    }
