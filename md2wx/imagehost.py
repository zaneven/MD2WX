"""
MD2WX 在线图床客户端 (通用自定义上传接口，纯标准库零第三方依赖)

设计参考 WePost 的图床能力：向一个可配置的上传接口 POST multipart/form-data，
从返回 JSON 中提取图片 URL。接口、鉴权方式、表单字段名与响应字段路径均可通过
环境变量 / .env 配置，从而对接自建图床、WePost 的 /api/uploads 或任意兼容服务。

配置项 (写入 .env 或进程环境变量)：
    IMAGE_HOST_UPLOAD_URL     必填，上传接口完整地址
    IMAGE_HOST_TOKEN          可选，鉴权令牌
    IMAGE_HOST_TOKEN_FIELD    可选，若设置则令牌作为表单字段发送，否则作为请求头发送
    IMAGE_HOST_AUTH_HEADER    可选，令牌请求头名，默认 Authorization
    IMAGE_HOST_AUTH_PREFIX    可选，令牌前缀，默认空 (如 Bearer 需显式设置为 "Bearer ")
    IMAGE_HOST_FILE_FIELD     可选，文件表单字段名，默认 file
    IMAGE_HOST_RESPONSE_PATH  可选，响应中图片 URL 的路径，支持点号嵌套，默认 url
    IMAGE_HOST_TIMEOUT        可选，请求超时秒数，默认 30

未配置 IMAGE_HOST_UPLOAD_URL 时，is_image_host_configured() 返回 False，
调用方应据此提示用户"暂不支持上传图片"。
"""
import json
import mimetypes
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse
from typing import Dict, List, Optional, Tuple

from .envutil import is_placeholder, load_env

DEFAULT_FILE_FIELD = "file"
DEFAULT_RESPONSE_PATH = "url"
DEFAULT_AUTH_HEADER = "Authorization"
DEFAULT_TIMEOUT = 30
_MULTIPART_BOUNDARY = "----WebKitFormBoundaryMD2WXImageHost"

CONFIG_HINT = (
    "未配置在线图床，暂不支持上传图片。"
    "请在 .env 中设置 IMAGE_HOST_UPLOAD_URL (可选 IMAGE_HOST_TOKEN) 后重试。"
)


class ImageHostConfig:
    """在线图床配置对象"""

    def __init__(
        self,
        upload_url: str,
        token: str = "",
        token_field: str = "",
        auth_header: str = DEFAULT_AUTH_HEADER,
        auth_prefix: str = "",
        file_field: str = DEFAULT_FILE_FIELD,
        response_path: str = DEFAULT_RESPONSE_PATH,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.upload_url = upload_url
        self.token = token
        self.token_field = token_field
        self.auth_header = auth_header
        self.auth_prefix = auth_prefix
        self.file_field = file_field
        self.response_path = response_path
        self.timeout = timeout

    def __repr__(self) -> str:  # pragma: no cover - 便于调试
        return f"ImageHostConfig(upload_url={self.upload_url!r}, file_field={self.file_field!r}, response_path={self.response_path!r})"


def _pick(env: Dict[str, str], key: str, default: str = "") -> str:
    val = env.get(key)
    if val is None:
        return default
    return val.strip()


def _parse_timeout(raw: str, default: int = DEFAULT_TIMEOUT) -> int:
    try:
        value = int(str(raw).strip())
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def get_image_host_config(env: Optional[Dict[str, str]] = None) -> Optional[ImageHostConfig]:
    """从环境变量/.env 解析图床配置；未配置返回 None"""
    env = env if env is not None else load_env()
    upload_url = _pick(env, "IMAGE_HOST_UPLOAD_URL")
    if is_placeholder(upload_url) or not upload_url.lower().startswith(("http://", "https://")):
        return None

    return ImageHostConfig(
        upload_url=upload_url,
        token=_pick(env, "IMAGE_HOST_TOKEN"),
        token_field=_pick(env, "IMAGE_HOST_TOKEN_FIELD"),
        auth_header=_pick(env, "IMAGE_HOST_AUTH_HEADER", DEFAULT_AUTH_HEADER) or DEFAULT_AUTH_HEADER,
        auth_prefix=env.get("IMAGE_HOST_AUTH_PREFIX", "") or "",
        file_field=_pick(env, "IMAGE_HOST_FILE_FIELD", DEFAULT_FILE_FIELD) or DEFAULT_FILE_FIELD,
        response_path=_pick(env, "IMAGE_HOST_RESPONSE_PATH", DEFAULT_RESPONSE_PATH) or DEFAULT_RESPONSE_PATH,
        timeout=_parse_timeout(env.get("IMAGE_HOST_TIMEOUT", ""), DEFAULT_TIMEOUT),
    )


def is_image_host_configured(env: Optional[Dict[str, str]] = None) -> bool:
    """图床是否已配置"""
    return get_image_host_config(env) is not None


def _build_multipart_body(
    fields: List[Tuple[str, str]],
    filename: str,
    mime_type: str,
    file_bytes: bytes,
    file_field: str,
    boundary: str = _MULTIPART_BOUNDARY,
) -> bytes:
    """构造 multipart/form-data 请求体（普通字段 + 单个文件字段）"""
    chunks: List[bytes] = []
    for name, value in fields:
        chunks.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )
    safe_name = os.path.basename(filename).replace("\\", "").replace('"', "") or "image.png"
    chunks.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{file_field}"; filename="{safe_name}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8")
    )
    chunks.append(file_bytes)
    chunks.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks)


def _extract_by_path(data, path: str) -> Optional[str]:
    """按点号路径从嵌套 JSON 中提取字符串值，支持列表下标 (如 data.0.url)"""
    current = data
    for segment in path.split("."):
        if isinstance(current, dict):
            if segment not in current:
                return None
            current = current[segment]
        elif isinstance(current, list):
            try:
                current = current[int(segment)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current if isinstance(current, str) and current else None


def upload_image_bytes(
    file_bytes: bytes,
    filename: str = "image.png",
    mime_type: Optional[str] = None,
    config: Optional[ImageHostConfig] = None,
) -> str:
    """将图片字节上传到在线图床，返回图片 URL"""
    cfg = config or get_image_host_config()
    if cfg is None:
        raise RuntimeError(CONFIG_HINT)

    mime = mime_type or mimetypes.guess_type(filename)[0] or "image/png"

    fields: List[Tuple[str, str]] = []
    headers = {
        "Content-Type": f"multipart/form-data; boundary={_MULTIPART_BOUNDARY}",
        # Cloudflare Bot Fight Mode 会拦截默认 Python-urllib UA (error 1010)，伪装为浏览器 UA
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 MD2WX",
    }
    if cfg.token:
        if cfg.token_field:
            fields.append((cfg.token_field, cfg.token))
        else:
            headers[cfg.auth_header] = f"{cfg.auth_prefix}{cfg.token}"

    body = _build_multipart_body(fields, filename, mime, file_bytes, cfg.file_field)
    req = urllib.request.Request(cfg.upload_url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        raise RuntimeError(f"图床上传失败 HTTP {e.code}: {detail or e.reason}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(f"图床返回非 JSON 响应: {raw[:200]}")

    url = _extract_by_path(data, cfg.response_path)
    if not url or not url.lower().startswith(("http://", "https://")):
        raise RuntimeError(
            f"图床响应中未找到图片地址 (response_path='{cfg.response_path}'): {raw[:200]}"
        )
    return url


def upload_image_file(filepath: str, config: Optional[ImageHostConfig] = None) -> str:
    """将本地图片文件上传到在线图床，返回图片 URL"""
    path = os.path.expanduser(filepath)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"图片文件不存在: {filepath}")
    filename = os.path.basename(path)
    mime = mimetypes.guess_type(filename)[0] or "image/png"
    with open(path, "rb") as f:
        file_bytes = f.read()
    return upload_image_bytes(file_bytes, filename, mime, config)


def download_image_bytes(url: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[bytes, str, str]:
    """
    下载在线图片，返回 (字节内容, 文件名, MIME 类型)。
    仅允许 http/https，用于把外链/图床图片转存到微信 CDN。
    """
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError(f"仅支持下载 http/https 图片: {url}")

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MD2WX Image Rehoster)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"下载外链图片失败 HTTP {e.code}: {url}")

    if not content:
        raise RuntimeError(f"下载外链图片为空: {url}")

    # 从 URL 路径推断文件名，回退到通用名
    path = urlparse(url).path or ""
    basename = os.path.basename(path) or "image"
    if "." not in basename:
        basename += mimetypes.guess_extension(content_type) or ".png"
    mime = content_type or mimetypes.guess_type(basename)[0] or "image/png"
    return content, basename, mime
