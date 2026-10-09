import { resolve } from 'node:path';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

const currentDir = fileURLToPath(new URL('.', import.meta.url));

// 版本单一数据源：pyproject.toml（CLI 与 Web 共用），构建期注入 __APP_VERSION__
const pyproject = readFileSync(resolve(currentDir, '../pyproject.toml'), 'utf8');
const appVersion = pyproject.match(/^version\s*=\s*"([^"]+)"/m)[1];
if (!appVersion) {
  throw new Error('无法从 pyproject.toml 解析 version 字段');
}

export default defineConfig({
  base: './',
  define: {
    __APP_VERSION__: JSON.stringify(appVersion)
  },
  server: {
    port: 3000,
    open: false,
    host: true,
    // 允许开发期导入 web/ 目录之外的 md2wx/themes/*.json (主题单一数据源)
    fs: {
      allow: [fileURLToPath(new URL('..', import.meta.url))]
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    rollupOptions: {
      input: {
        main: resolve(currentDir, 'index.html'),
        studio: resolve(currentDir, 'studio.html')
      }
    }
  }
});
