# MD2WX 图床 - Cloudflare Worker + R2

一个 ~150 行的 Worker，把 R2 包装成 MD2WX 可直接调用的简单图床接口（与 WePost `/api/uploads` 同款契约）。
R2 凭据只活在 Worker 侧，客户端零 S3 签名、零密钥暴露。

## 接口

| 方法 | 路径 | 鉴权 | 用途 |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/uploads` | 令牌 (`Authorization` / `Bearer`) | CLI 私密上传 |
| `POST` | `/api/public/uploads` | 免密，仅 Origin 白名单 | Web 静态站上传（不泄露密钥） |
| `GET` | `/images/<key>` | 无 | 取图，`Cache-Control: immutable` |
| `GET` | `/health` | 无 | 健康检查 |

两条上传路由均返回 `{ url }`，multipart 字段名为 `file`。

## 部署（约 2 分钟）

前置：已安装 Node.js，浏览器登录 Cloudflare。

```bash
cd cloudflare/r2-imagehost
npx wrangler login                         # 首次登录
npx wrangler r2 bucket create md2wx-images # 创建 R2 桶（名字与 wrangler.toml 一致）
# 可选：设上传令牌，供 CLI 私密上传使用（Web 走免密公开路由，不需要令牌）
npx wrangler secret put UPLOAD_TOKEN        # 粘贴一段随机串
npx wrangler deploy
```

部署后控制台会输出 `https://md2wx-imagehost.<your-subdomain>.workers.dev`，自测：

```bash
# 免密公开路由（模拟浏览器来源）
curl -X POST https://md2wx-imagehost.<sub>.workers.dev/api/public/uploads \
  -H "Origin: https://md2wx.zaneven.com" -F "file=@/path/to/photo.png"
# -> {"url":"https://md2wx-imagehost.<sub>.workers.dev/images/2026/09/23/xxxx.png"}

# 令牌私密路由
curl -X POST https://md2wx-imagehost.<sub>.workers.dev/api/uploads \
  -H "Authorization: Bearer <UPLOAD_TOKEN>" -F "file=@/path/to/photo.png"
```

## 接到 MD2WX

### CLI（令牌私密路由）

仓库根 `.env`：

```bash
IMAGE_HOST_UPLOAD_URL=https://md2wx-imagehost.<sub>.workers.dev/api/uploads
IMAGE_HOST_TOKEN=<UPLOAD_TOKEN>
IMAGE_HOST_AUTH_PREFIX=Bearer
```

### Web Studio（免密公开路由）

本地开发：`web/.env.local`（已 gitignore）

```bash
VITE_IMAGE_HOST_UPLOAD_URL=https://md2wx-imagehost.<sub>.workers.dev/api/public/uploads
```

线上（GitHub Pages）：在仓库 Settings → Variables 设置 `IMAGE_HOST_PUBLIC_UPLOAD_URL` 为公开路由地址，
`.github/workflows/deploy.yml` 会自动透传为 `VITE_IMAGE_HOST_UPLOAD_URL`。

## 生产加固

- 对 `/api/public/uploads` 配置 Cloudflare **Rate Limiting** 规则，限制单 IP 上传频率（免费额度 1 条）。
- 在 Cloudflare 给 Worker 绑定自定义域名（如 `img.你的域.com`），把 `PUBLIC_BASE` 设为该域名。
- 收紧 `ALLOWED_ORIGINS` 只保留你的站点域名。
