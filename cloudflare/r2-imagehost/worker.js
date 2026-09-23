/**
 * MD2WX 图床 - Cloudflare Worker + R2 代理
 *
 * 提供两条上传路由，兼顾 Web 静态站与 CLI：
 *   POST /api/uploads         令牌鉴权（Authorization: <token> / Bearer <token>），供 CLI 私密使用
 *   POST /api/public/uploads  免密公开上传（仅校验 Origin 白名单），供 GitHub Pages 静态站使用
 *   GET  /images/<key>        从 R2 取图（Cache-Control: immutable）
 *   GET  /health              健康检查
 *
 * R2 凭据仅保存在 Worker 侧，客户端无需 S3 签名，也不暴露任何敏感密钥。
 *
 * 变量 (wrangler.toml [vars])：
 *   PUBLIC_BASE       图片访问基础域名，留空则用 *.workers.dev
 *   ALLOWED_ORIGINS   公开上传路由允许的站点来源，逗号分隔 (如 https://md2wx.zaneven.com,http://localhost:3000)
 * 密钥 (wrangler secret)：
 *   UPLOAD_TOKEN      设置后 /api/uploads 需携带；不设则 /api/uploads 也免密
 *
 * 生产加固建议：对 /api/public/uploads 配置 Cloudflare Rate Limiting 规则，限制单 IP 上传频率。
 */

const ALLOWED_MIME = ['image/png', 'image/jpeg', 'image/webp', 'image/gif'];
const MAX_BYTES = 10 * 1024 * 1024; // 10MB

function parseOrigins(env) {
  return String(env.ALLOWED_ORIGINS || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

function corsHeaders(request, env) {
  const origin = request.headers.get('Origin') || '';
  const allowed = parseOrigins(env);
  let allowOrigin = '*';
  if (allowed.length > 0) {
    allowOrigin = allowed.includes(origin) ? origin : allowed[0];
  }
  return {
    'Access-Control-Allow-Origin': allowOrigin,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  };
}

function json(data, status = 200, cors = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...cors },
  });
}

function tokenAuthorized(request, env) {
  const token = env.UPLOAD_TOKEN;
  if (!token) return true; // 未设置令牌则不鉴权
  const auth = request.headers.get('Authorization') || '';
  const bare = auth.startsWith('Bearer ') ? auth.slice(7).trim() : auth.trim();
  return bare === token;
}

/** 公开路由来源校验：要求 Origin 存在且在白名单内（未配置白名单则不校验） */
function originAllowed(request, env) {
  const allowed = parseOrigins(env);
  if (allowed.length === 0) return true;
  const origin = request.headers.get('Origin') || '';
  return allowed.includes(origin);
}

function extFromType(type) {
  return ({ 'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif' })[type] || 'png';
}

async function handleUpload(request, env, url, cors) {
  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ error: '请求不是合法的 multipart/form-data' }, 400, cors);
  }
  const file = form.get('file') || form.get('image') || form.get('media');
  if (!file || typeof file === 'string') {
    return json({ error: '未找到文件字段 (file)' }, 400, cors);
  }
  if (!ALLOWED_MIME.includes(file.type)) {
    return json({ error: '仅支持 PNG / JPG / WebP / GIF 图片' }, 400, cors);
  }
  if (file.size > MAX_BYTES) {
    return json({ error: '图片不能超过 10MB' }, 413, cors);
  }

  const ext = extFromType(file.type);
  const now = new Date();
  const y = now.getUTCFullYear();
  const m = String(now.getUTCMonth() + 1).padStart(2, '0');
  const d = String(now.getUTCDate()).padStart(2, '0');
  const rnd = crypto.randomUUID().replace(/-/g, '').slice(0, 16);
  const key = `${y}/${m}/${d}/${rnd}.${ext}`;

  await env.IMAGES.put(key, file.stream(), {
    httpMetadata: { contentType: file.type },
    customMetadata: { filename: file.name || '', size: String(file.size) },
  });

  const base = (env.PUBLIC_BASE || `${url.protocol}//${url.host}`).replace(/\/$/, '');
  return json({ url: `${base}/images/${key}` }, 201, cors);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = corsHeaders(request, env);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors });
    }

    if (url.pathname === '/' || url.pathname === '/health') {
      return json({ ok: true, service: 'md2wx-r2-imagehost' });
    }

    // 取图：GET /images/<key>
    if (request.method === 'GET' && url.pathname.startsWith('/images/')) {
      const key = decodeURIComponent(url.pathname.replace('/images/', ''));
      if (!key) return json({ error: '缺少图片 key' }, 404);
      const obj = await env.IMAGES.get(key);
      if (!obj) return json({ error: '图片不存在' }, 404);
      return new Response(obj.body, {
        headers: {
          'Content-Type': obj.httpMetadata?.contentType || 'application/octet-stream',
          'Cache-Control': 'public, max-age=31536000, immutable',
          ...cors,
        },
      });
    }

    // 私密上传：POST /api/uploads（令牌鉴权，供 CLI）
    if (request.method === 'POST' && url.pathname === '/api/uploads') {
      if (!tokenAuthorized(request, env)) {
        return json({ error: '未授权：令牌缺失或不正确' }, 401, cors);
      }
      return handleUpload(request, env, url, cors);
    }

    // 公开上传：POST /api/public/uploads（免密，仅 Origin 白名单，供 Web 静态站）
    if (request.method === 'POST' && url.pathname === '/api/public/uploads') {
      if (!originAllowed(request, env)) {
        return json({ error: '来源站点不在允许列表内' }, 403, cors);
      }
      return handleUpload(request, env, url, cors);
    }

    return json({ error: '未匹配的接口路由' }, 404, cors);
  },
};
