/**
 * MD2WX 在线图床客户端 (浏览器端，纯原生 fetch，零第三方依赖)
 *
 * 设计参考 WePost 的图床能力：向一个可配置的上传接口 POST multipart/form-data，
 * 从返回 JSON 中提取图片 URL。接口、鉴权方式、表单字段名与响应字段路径均通过
 * Vite 构建期环境变量 (VITE_IMAGE_HOST_*) 注入，运行时只读不可改。
 *
 * 配置项 (写入 .env 或 GitHub Pages 构建环境变量)：
 *   VITE_IMAGE_HOST_UPLOAD_URL     必填，上传接口完整地址
 *   VITE_IMAGE_HOST_TOKEN          可选，鉴权令牌 (注意: 会被打包进公开产物，仅用于无敏感性的公开端点)
 *   VITE_IMAGE_HOST_TOKEN_FIELD    可选，令牌作为表单字段发送；否则作为请求头发送
 *   VITE_IMAGE_HOST_AUTH_HEADER    可选，令牌请求头名，默认 Authorization
 *   VITE_IMAGE_HOST_AUTH_PREFIX    可选，令牌前缀，默认空 (如需 "Bearer " 显式设置)
 *   VITE_IMAGE_HOST_FILE_FIELD     可选，文件表单字段名，默认 file
 *   VITE_IMAGE_HOST_RESPONSE_PATH  可选，响应中图片 URL 路径，支持点号嵌套，默认 url
 *
 * 未配置 UPLOAD_URL 时，isImageHostConfigured() 返回 false，
 * 上传入口应提示用户"未配置图床，暂不支持上传图片"。
 */

const ENV = import.meta.env || {};

const UPLOAD_URL = String(ENV.VITE_IMAGE_HOST_UPLOAD_URL || '').trim();
const TOKEN = String(ENV.VITE_IMAGE_HOST_TOKEN || '').trim();
const TOKEN_FIELD = String(ENV.VITE_IMAGE_HOST_TOKEN_FIELD || '').trim();
const AUTH_HEADER = String(ENV.VITE_IMAGE_HOST_AUTH_HEADER || 'Authorization').trim() || 'Authorization';
const AUTH_PREFIX = ENV.VITE_IMAGE_HOST_AUTH_PREFIX != null ? String(ENV.VITE_IMAGE_HOST_AUTH_PREFIX) : '';
const FILE_FIELD = String(ENV.VITE_IMAGE_HOST_FILE_FIELD || 'file').trim() || 'file';
const RESPONSE_PATH = String(ENV.VITE_IMAGE_HOST_RESPONSE_PATH || 'url').trim() || 'url';

/** 兼容的图片 MIME 与体积上限 (与 WePost 图床策略对齐) */
export const IMAGE_HOST_ACCEPT = 'image/png,image/jpeg,image/webp,image/gif';
export const IMAGE_HOST_MAX_BYTES = 10 * 1024 * 1024; // 10MB

export const IMAGE_HOST_UNCONFIGURED_HINT =
  '未配置在线图床，暂不支持上传图片。请在 .env 中设置 IMAGE_HOST_UPLOAD_URL (构建时用 VITE_ 前缀) 后重试。';

/**
 * 图床是否已配置（UPLOAD_URL 非空且非占位符）
 */
export function isImageHostConfigured() {
  if (!UPLOAD_URL) return false;
  return !/^(your_|<)/i.test(UPLOAD_URL) && /^https?:\/\//i.test(UPLOAD_URL);
}

/**
 * 客户端预校验：MIME 类型 + 体积，返回错误文案（null = 通过）
 */
export function validateImageFile(file) {
  if (!IMAGE_HOST_ACCEPT.split(',').includes(file.type)) {
    return '仅支持 PNG / JPG / WebP / GIF 图片';
  }
  if (file.size > IMAGE_HOST_MAX_BYTES) {
    return '图片不能超过 10MB';
  }
  return null;
}

/** 校验用户粘贴的图片链接（仅 http/https） */
export function isValidImageUrl(url) {
  return /^https?:\/\/\S+$/i.test((url || '').trim());
}

/** 按点号路径从嵌套 JSON 中提取字符串值，支持列表下标 (如 data.0.url) */
function extractByPath(data, path) {
  let current = data;
  for (const segment of String(path).split('.')) {
    if (current == null) return null;
    if (Array.isArray(current)) {
      const idx = Number(segment);
      if (Number.isNaN(idx) || idx < 0 || idx >= current.length) return null;
      current = current[idx];
    } else if (typeof current === 'object') {
      if (!(segment in current)) return null;
      current = current[segment];
    } else {
      return null;
    }
  }
  return typeof current === 'string' ? current : null;
}

/**
 * 上传本地图片到图床，成功返回可插入 Markdown 的图片 URL
 * @param {File} file
 * @returns {Promise<string>}
 */
export async function uploadImageFile(file) {
  if (!isImageHostConfigured()) {
    throw new Error(IMAGE_HOST_UNCONFIGURED_HINT);
  }
  const precheckError = validateImageFile(file);
  if (precheckError) throw new Error(precheckError);

  const form = new FormData();
  form.append(FILE_FIELD, file);
  if (TOKEN && TOKEN_FIELD) {
    form.append(TOKEN_FIELD, TOKEN);
  }

  const headers = {};
  if (TOKEN && !TOKEN_FIELD) {
    headers[AUTH_HEADER] = `${AUTH_PREFIX}${TOKEN}`;
  }

  let res;
  try {
    res = await fetch(UPLOAD_URL, { method: 'POST', body: form, headers });
  } catch (err) {
    throw new Error(`图床网络请求失败，请检查 CORS 跨域或接口可用性 (${UPLOAD_URL})`);
  }

  if (!res.ok) {
    let message = `图床上传失败 (${res.status})`;
    try {
      const body = await res.json();
      if (body && body.error) message = body.error;
    } catch {
      // 非 JSON 响应，保留状态码文案
    }
    throw new Error(message);
  }

  let data;
  try {
    data = await res.json();
  } catch {
    throw new Error('图床返回非 JSON 响应');
  }

  const url = extractByPath(data, RESPONSE_PATH);
  if (!url || !/^https?:\/\//i.test(url)) {
    throw new Error(`图床响应中未找到图片地址 (response_path='${RESPONSE_PATH}')`);
  }
  return url;
}
