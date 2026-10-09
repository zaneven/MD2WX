/**
 * Node ESM JSON 导入加载器：让 Node 原生运行 Vite 风格的 `import x from './a.json'`
 * (供 golden 一致性测试复用 src/core/* 源码，不引入任何构建步骤)
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

export async function load(url, context, next) {
  if (url.endsWith('.json')) {
    const src = readFileSync(fileURLToPath(url), 'utf8');
    return { format: 'module', shortCircuit: true, source: `export default ${src};` };
  }
  return next(url, context);
}
