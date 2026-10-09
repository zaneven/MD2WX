/**
 * 注册 JSON 导入加载器 (node --import 入口)
 */
import { register } from 'node:module';

register('./json-loader.mjs', import.meta.url);
