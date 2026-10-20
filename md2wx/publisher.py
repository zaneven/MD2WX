"""
MD2WX 微信公众平台草稿箱发布服务
支持新建草稿 (draft/add) 与覆盖更新已有草稿 (draft/update)
"""
import json
import urllib.request
from typing import Callable, Dict, Any, Optional
from .uploader import upload_cover_material, WeChatApiError, TOKEN_EXPIRED_ERRCODES
from .envutil import load_env


def _build_article_object(
    title: str,
    content_html: str,
    author: str,
    digest: str,
    thumb_media_id: str,
    content_source_url: str,
    pic_crop_235_1: Optional[str] = None,
    pic_crop_1_1: Optional[str] = None,
) -> Dict[str, Any]:
    """构造微信图文 article 对象 (add 与 update 共用)"""
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
    return article_obj


def _post_draft_api(
    token: str,
    payload: Dict[str, Any],
    proxy_action: str,
    direct_action: str,
) -> Dict[str, Any]:
    """
    按是否配置代理提交草稿操作：
    - 代理模式: {action, token, payload}，与既有 draft / draft_get 网关约定一致
    - 直连模式: https://api.weixin.qq.com/cgi-bin/<direct_action>?access_token=...
    """
    proxy_url = load_env().get("WECHAT_PROXY_URL")
    if proxy_url and proxy_url.strip():
        gateway_body = {"action": proxy_action, "token": token, "payload": payload}
        if payload.get("media_id"):
            # 兼容只读取顶层 mediaId 的代理实现
            gateway_body["mediaId"] = payload["media_id"]
        req = urllib.request.Request(
            proxy_url.strip(),
            data=json.dumps(gateway_body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
            }
        )
    else:
        req = urllib.request.Request(
            f"https://api.weixin.qq.com/cgi-bin/{direct_action}?access_token={token}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"}
        )

    res_raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    return json.loads(res_raw)


def _fetch_preview_url(token: str, media_id: str) -> str:
    """读取草稿详情获取微信官方临时预览 URL；失败不影响主流程"""
    proxy_url = load_env().get("WECHAT_PROXY_URL")
    try:
        if proxy_url and proxy_url.strip():
            req = urllib.request.Request(
                proxy_url.strip(),
                data=json.dumps({"action": "draft_get", "token": token, "mediaId": media_id}).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                }
            )
        else:
            req = urllib.request.Request(
                f"https://api.weixin.qq.com/cgi-bin/draft/get?access_token={token}",
                data=json.dumps({"media_id": media_id}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
        verify_res = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
        news_items = verify_res.get("news_item", [])
        if news_items:
            return news_items[0].get("url", "")
    except Exception:
        pass
    return ""


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
    content_source_url: str = "",
    token_refresher: Optional[Callable[[], str]] = None,
    update_media_id: Optional[str] = None,
    update_index: int = 0,
) -> Dict[str, Any]:
    """
    提交文章到微信公众号草稿箱。
    默认新建草稿 (draft/add)；传入 update_media_id 时覆盖更新该草稿 (draft/update)，
    避免同一篇文章反复发布后后台堆积副本。

    支持传入 pic_crop_235_1 与 pic_crop_1_1 精确设定微信头条与次条/会话方图的裁切坐标。
    token_refresher: 凭据强制刷新回调；draft 链路遇 token 失效 (40001/42001/40014)
    时刷新凭据并整链路重试一次，覆盖封面素材上传与草稿提交两个消费环节。
    """
    for attempt in range(2):
        try:
            return _publish_draft_once(
                token, title, content_html, author, digest,
                thumb_media_id, cover_image_path,
                pic_crop_235_1, pic_crop_1_1, content_source_url,
                update_media_id, update_index,
            )
        except WeChatApiError as e:
            if attempt == 0 and token_refresher and e.errcode in TOKEN_EXPIRED_ERRCODES:
                token = token_refresher()
                continue
            raise


def _publish_draft_once(
    token: str,
    title: str,
    content_html: str,
    author: str,
    digest: str,
    thumb_media_id: Optional[str],
    cover_image_path: Optional[str],
    pic_crop_235_1: Optional[str],
    pic_crop_1_1: Optional[str],
    content_source_url: str,
    update_media_id: Optional[str] = None,
    update_index: int = 0,
) -> Dict[str, Any]:
    """单次完整提交流程：封面素材上传 (可选) + draft/add 或 draft/update + 草稿详情回读"""
    # 1. 如果未直接提供 thumb_media_id，尝试上传封面图
    if not thumb_media_id and cover_image_path:
        thumb_media_id = upload_cover_material(token, cover_image_path)

    if not thumb_media_id:
        raise ValueError("微信公众号图文草稿必须指定封面图 (需提供 thumb_media_id 或有效的 cover_image_path)")

    article_obj = _build_article_object(
        title, content_html, author, digest, thumb_media_id,
        content_source_url, pic_crop_235_1, pic_crop_1_1,
    )

    is_update = bool(update_media_id)
    if is_update:
        payload: Dict[str, Any] = {
            "media_id": update_media_id,
            "index": max(0, int(update_index or 0)),
            "articles": article_obj,
        }
        res = _post_draft_api(token, payload, "draft_update", "draft/update")
        if res.get("errcode") or res.get("error"):
            raise WeChatApiError(
                f"微信草稿更新失败: {res.get('errmsg') or res.get('error') or res}",
                errcode=res.get("errcode"),
            )
        draft_media_id = update_media_id
    else:
        payload = {"articles": [article_obj]}
        res = _post_draft_api(token, payload, "draft", "draft/add")
        draft_media_id = res.get("media_id")
        if res.get("errcode") or res.get("error") or not draft_media_id:
            raise WeChatApiError(
                f"微信草稿提交失败: {res.get('errmsg') or res.get('error') or res}",
                errcode=res.get("errcode"),
            )

    # 2. 尝试读取草稿详情获取微信官方临时预览 URL
    preview_url = _fetch_preview_url(token, draft_media_id)

    return {
        "media_id": draft_media_id,
        "preview_url": preview_url,
        "title": title,
        "author": author,
        "thumb_media_id": thumb_media_id,
        "pic_crop_235_1": pic_crop_235_1,
        "pic_crop_1_1": pic_crop_1_1,
        "updated": is_update,
    }
