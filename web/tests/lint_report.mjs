/**
 * Lint 报告 harness：用 Web 端 lint.js 对输入 Markdown 产出问题清单，
 * 输出 JSON 供 tests/test_lint_consistency.py 与 Python 端 linter.py 逐条比对。
 * 用法: node --import ./tests/register-loader.mjs ./tests/lint_report.mjs <input.md>
 */
import { readFileSync } from 'node:fs';
import { lintMarkdown } from '../src/core/lint.js';

const inputPath = process.argv[2];
if (!inputPath) {
  console.error('usage: node --import ./tests/register-loader.mjs ./tests/lint_report.mjs <input.md>');
  process.exit(2);
}

const raw = readFileSync(inputPath, 'utf8');
process.stdout.write(JSON.stringify({ issues: lintMarkdown(raw) }));
