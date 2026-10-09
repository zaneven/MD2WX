/**
 * MD2WX Web Studio - 版本速递对话框逻辑 (Changelog Modal)
 * 版本徽章入口、弹窗开关与全局 Esc 快捷键关闭
 */

/**
 * 初始化版本速递对话框
 */
export function initChangelogModal() {
  const badgeBtn = document.getElementById('btn-version-badge');
  const overlay = document.getElementById('changelog-modal-overlay');
  const closeBtn = document.getElementById('btn-close-changelog-modal');

  if (!badgeBtn || !overlay) return;

  function openModal() {
    overlay.classList.add('active');
  }

  function closeModal() {
    overlay.classList.remove('active');
  }

  badgeBtn.addEventListener('click', openModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeModal();
  });

  // 全局 Esc 快捷键关闭弹窗
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const coverOverlay = document.getElementById('cover-modal-overlay');
      if (coverOverlay && coverOverlay.classList.contains('active')) {
        coverOverlay.classList.remove('active');
      }
      if (overlay.classList.contains('active')) {
        closeModal();
      }
    }
  });
}
