/**
 * MD2WX 富文本剪贴板注入模块
 * 将生成的纯 Inline CSS HTML 以 text/html 规范写入系统剪贴板，支持直接在微信公众号后台按 Cmd+V 粘贴
 */

export async function copyWechatHtml(html, fallbackPlainText = '') {
  // 现代浏览器标准 API: navigator.clipboard.write + ClipboardItem
  if (navigator.clipboard && window.ClipboardItem) {
    try {
      const htmlBlob = new Blob([html], { type: 'text/html' });
      const textBlob = new Blob([fallbackPlainText || html.replace(/<[^>]+>/g, '')], {
        type: 'text/plain',
      });

      const item = new ClipboardItem({
        'text/html': htmlBlob,
        'text/plain': textBlob,
      });

      await navigator.clipboard.write([item]);
      return { success: true, method: 'ClipboardItem' };
    } catch (err) {
      console.warn('ClipboardItem 写入失败，尝试 contenteditable 回退方案:', err);
    }
  }

  // 兼容回退方案：隐藏 contenteditable DOM 复制
  try {
    const container = document.createElement('div');
    container.style.position = 'fixed';
    container.style.left = '-9999px';
    container.style.top = '-9999px';
    container.style.opacity = '0';
    container.style.pointerEvents = 'none';
    container.contentEditable = 'true';
    container.innerHTML = html;

    document.body.appendChild(container);

    const range = document.createRange();
    range.selectNodeContents(container);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);

    const successful = document.execCommand('copy');
    selection.removeAllRanges();
    document.body.removeChild(container);

    if (successful) {
      return { success: true, method: 'execCommand' };
    } else {
      throw new Error('execCommand 返回 false');
    }
  } catch (fallbackErr) {
    console.error('富文本复制失败:', fallbackErr);
    return { success: false, error: fallbackErr.message };
  }
}

/**
 * 导出 HTML 文件下载
 */
export function downloadHtmlFile(html, filename = 'article-wechat.html') {
  const fullDoc = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MD2WX 排版导出</title>
</head>
<body style="margin: 0; padding: 20px; display: flex; justify-content: center; background-color: #f8fafc;">
  <div style="width: 100%; max-width: 677px;">
${html}
  </div>
</body>
</html>`;

  const blob = new Blob([fullDoc], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
