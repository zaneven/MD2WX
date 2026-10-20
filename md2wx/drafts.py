"""
MD2WX 微信草稿箱管理服务

提供草稿列表、覆盖更新与删除能力，并维护「本地文章 -> 草稿 ID」映射，
让同一篇 Markdown 重复发布时覆盖原草稿，而不是在后台不断堆积副本。

所有网络调用均为纯标准库实现，且与 publisher/uploader 保持一致：
配置了 WECHAT_PROXY_URL 时走代理网关，否则直连微信官方接口。
"""
import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .envutil import load_env
from .uploader import WeChatApiError, TOKEN_EXPIRED_ERRCODES

# 本地「文章 -> 草稿」映射缓存：按输入文件绝对路径记录最近一次发布的草稿
DRAFT_STATE_PATH = Path.home() / ".config" / "md2wx" / "drafts.json"
# 微信 draft/batchget 单页上限
DRAFT_PAGE_LIMIT = 20
# 草稿已被删除/不存在 (draft/update 时命中该错误码说明本地映射已过期)
DRAFT_NOT_FOUND_ERRCODES = (40007,)


def _proxy_url() -> Optional[str]:
    proxy = load_env().get("WECHAT_PROXY_URL")
    return proxy.strip() if proxy and proxy.strip() else None


def _request(
    token: str,
    api_action: str,
    payload: Dict[str, Any],
    proxy_action: str,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    调用微信草稿箱接口，按是否配置代理选择请求通道。
    proxy_action 与既有 draft / draft_get 代理约定保持一致。
    """
    proxy_url = _proxy_url()
    if proxy_url:
        body = {"action": proxy_action, "token": token, "payload": payload}
        media_id = payload.get("media_id")
        if media_id:
            # 兼容只读取顶层 mediaId 的代理实现
            body["mediaId"] = media_id
        req = urllib.request.Request(
            proxy_url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            },
        )
    else:
        req = urllib.request.Request(
            f"https://api.weixin.qq.com/cgi-bin/{api_action}?access_token={token}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    res_raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")
    res = json.loads(res_raw)
    if res.get("errcode") or res.get("error"):
        raise WeChatApiError(
            f"微信草稿箱操作失败: {res.get('errmsg') or res.get('error') or res}",
            errcode=res.get("errcode"),
        )
    return res


def _with_token_retry(
    call: Callable[[str], Dict[str, Any]],
    token: str,
    token_refresher: Optional[Callable[[], str]],
) -> Dict[str, Any]:
    """凭据失效 (40001/42001/40014) 时刷新 token 并重试一次"""
    try:
        return call(token)
    except WeChatApiError as e:
        if token_refresher and e.errcode in TOKEN_EXPIRED_ERRCODES:
            return call(token_refresher())
        raise


def _normalize_item(entry: Dict[str, Any]) -> Dict[str, Any]:
    """把 batchget 单条记录归一化为 CLI 展示需要的字段"""
    content = entry.get("content") or {}
    news_items = content.get("news_item") or []
    first = news_items[0] if news_items else {}
    return {
        "media_id": entry.get("media_id", ""),
        "title": first.get("title", ""),
        "author": first.get("author", ""),
        "digest": first.get("digest", ""),
        "url": first.get("url", ""),
        "update_time": entry.get("update_time", 0) or 0,
        "article_count": len(news_items),
    }


def list_drafts(
    token: str,
    offset: int = 0,
    count: int = 10,
    token_refresher: Optional[Callable[[], str]] = None,
) -> Dict[str, Any]:
    """
    列出草稿箱 (draft/batchget)。
    必须取回正文才能拿到标题，因此固定 no_content=0；单页数量受微信上限约束。
    """
    safe_count = max(1, min(int(count or 1), DRAFT_PAGE_LIMIT))
    payload = {"offset": max(0, int(offset or 0)), "count": safe_count, "no_content": 0}

    res = _with_token_retry(
        lambda t: _request(t, "draft/batchget", payload, "draft_batchget"),
        token,
        token_refresher,
    )
    items = [_normalize_item(entry) for entry in (res.get("item") or [])]
    return {
        "total_count": res.get("total_count", len(items)),
        "item_count": res.get("item_count", len(items)),
        "items": items,
    }


def get_draft(
    token: str,
    media_id: str,
    token_refresher: Optional[Callable[[], str]] = None,
) -> Dict[str, Any]:
    """读取单篇草稿详情 (draft/get)"""
    res = _with_token_retry(
        lambda t: _request(t, "draft/get", {"media_id": media_id}, "draft_get"),
        token,
        token_refresher,
    )
    news_items = res.get("news_item") or []
    first = news_items[0] if news_items else {}
    return {
        "media_id": media_id,
        "news_items": news_items,
        "title": first.get("title", ""),
        "url": first.get("url", ""),
    }


def update_draft(
    token: str,
    media_id: str,
    article: Dict[str, Any],
    index: int = 0,
    token_refresher: Optional[Callable[[], str]] = None,
) -> Dict[str, Any]:
    """
    覆盖更新已有草稿 (draft/update)。
    注意微信此处字段是单数 articles 对象，与 draft/add 的 articles 数组不同。
    """
    payload = {
        "media_id": media_id,
        "index": max(0, int(index or 0)),
        "articles": article,
    }
    _with_token_retry(
        lambda t: _request(t, "draft/update", payload, "draft_update"),
        token,
        token_refresher,
    )
    return {"media_id": media_id, "index": payload["index"]}


def delete_draft(
    token: str,
    media_id: str,
    token_refresher: Optional[Callable[[], str]] = None,
) -> Dict[str, Any]:
    """删除草稿 (draft/delete)"""
    _with_token_retry(
        lambda t: _request(t, "draft/delete", {"media_id": media_id}, "draft_delete"),
        token,
        token_refresher,
    )
    return {"media_id": media_id}


# ---------------------------------------------------------------------------
# 本地映射：记录每个 Markdown 文件最近一次发布/更新的草稿 ID
# ---------------------------------------------------------------------------

def draft_state_key(input_path: Optional[str], title: str = "") -> Optional[str]:
    """
    生成映射键：优先使用输入文件绝对路径；从 stdin 读入时退化为标题键。
    标题为空且无文件时不记录，避免误覆盖无关草稿。
    """
    if input_path:
        try:
            return "file:" + str(Path(input_path).expanduser().resolve())
        except OSError:
            return None
    title = (title or "").strip()
    return f"title:{title}" if title else None


def _load_state() -> Dict[str, Any]:
    try:
        with open(DRAFT_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"version": 1, "items": {}}
    if not isinstance(data, dict):
        return {"version": 1, "items": {}}
    items = data.get("items")
    if not isinstance(items, dict):
        data["items"] = {}
    data.setdefault("version", 1)
    return data


def _save_state(state: Dict[str, Any]) -> None:
    """原子写入映射缓存；失败不影响发布主流程"""
    try:
        DRAFT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = DRAFT_STATE_PATH.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, DRAFT_STATE_PATH)
    except Exception:
        pass


def get_last_draft(key: Optional[str]) -> Optional[Dict[str, Any]]:
    """读取指定文件上一次发布对应的草稿记录"""
    if not key:
        return None
    entry = _load_state().get("items", {}).get(key)
    return entry if isinstance(entry, dict) and entry.get("media_id") else None


def record_last_draft(key: Optional[str], media_id: str, title: str = "") -> None:
    """记录/刷新文件与草稿的对应关系"""
    if not key or not media_id:
        return
    state = _load_state()
    state.setdefault("items", {})[key] = {
        "media_id": media_id,
        "title": title,
        "updated_at": int(time.time()),
    }
    _save_state(state)


def forget_draft(media_id: str) -> int:
    """按草稿 ID 清除全部本地映射，返回清除条数 (删除草稿后调用)"""
    if not media_id:
        return 0
    state = _load_state()
    items = state.get("items", {})
    stale = [key for key, entry in items.items() if isinstance(entry, dict) and entry.get("media_id") == media_id]
    for key in stale:
        items.pop(key, None)
    if stale:
        _save_state(state)
    return len(stale)


def forget_key(key: Optional[str]) -> None:
    """清除指定文件的映射 (例如草稿已被后台删除、自动续更失败时)"""
    if not key:
        return
    state = _load_state()
    items = state.get("items", {})
    if items.pop(key, None) is not None:
        _save_state(state)


def list_local_mappings() -> Dict[str, Dict[str, Any]]:
    """返回 media_id -> 本地映射记录，供草稿列表标注「本机可续更」"""
    result: Dict[str, Dict[str, Any]] = {}
    for key, entry in _load_state().get("items", {}).items():
        if isinstance(entry, dict) and entry.get("media_id"):
            record = dict(entry)
            record["key"] = key
            result[entry["media_id"]] = record
    return result
