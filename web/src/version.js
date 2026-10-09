/**
 * MD2WX - 全局版本号注入模块
 * 版本单一数据源为 pyproject.toml：vite.config.js 构建期读取并注入
 * __APP_VERSION__，页面内禁止再硬编码版本号，统一用 data 属性占位。
 *
 * 用法（HTML）：
 *   <span data-app-version></span>          -> v1.3.0
 *   <span data-app-version-plain></span>    -> 1.3.0
 *   <span data-app-version-minor></span>    -> 1.3.x
 *   <button data-app-version-title></button> -> title 属性自动带版本号
 */

/* global __APP_VERSION__ */
const APP_VERSION =
  typeof __APP_VERSION__ === 'string' ? __APP_VERSION__ : '0.0.0';

export { APP_VERSION };

/**
 * 扫描并填充页面中所有版本占位元素（两个页面入口各调用一次）
 * @param {ParentNode} root
 */
export function applyVersion(root = document) {
  root.querySelectorAll('[data-app-version]').forEach((el) => {
    el.textContent = `v${APP_VERSION}`;
  });
  root.querySelectorAll('[data-app-version-plain]').forEach((el) => {
    el.textContent = APP_VERSION;
  });
  root.querySelectorAll('[data-app-version-minor]').forEach((el) => {
    const [major, minor] = APP_VERSION.split('.');
    el.textContent = `${major}.${minor}.x`;
  });
  root.querySelectorAll('[data-app-version-title]').forEach((el) => {
    el.title = `点击查看 MD2WX v${APP_VERSION} 版本亮点与更新日志`;
  });
}
