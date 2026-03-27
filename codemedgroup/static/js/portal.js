/* CodeMed Group — Shared Portal JS */
'use strict';

// ── Copy to clipboard ─────────────────────────────────────────
window.copyText = function(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn ? btn.textContent : null;
    if (btn) { btn.textContent = 'Copied!'; btn.style.color = 'var(--green)'; }
    setTimeout(() => {
      if (btn) { btn.textContent = orig; btn.style.color = ''; }
    }, 1800);
  });
};

// ── Format numbers ────────────────────────────────────────────
window.fmt = function(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return String(n);
};

// ── Animate counter ───────────────────────────────────────────
window.animateCounter = function(el, target, duration = 1000) {
  const start = performance.now();
  const isFloat = String(target).includes('.');
  const from = 0;
  function step(ts) {
    const progress = Math.min((ts - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    const val = from + (target - from) * ease;
    el.textContent = isFloat ? val.toFixed(3) : Math.floor(val).toLocaleString();
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = isFloat ? target.toFixed(3) : target.toLocaleString();
  }
  requestAnimationFrame(step);
};

// ── Toast notifications ───────────────────────────────────────
window.toast = function(message, type = 'info', duration = 3000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
    document.body.appendChild(container);
  }
  const colors = {
    info: 'var(--blue-glow)', success: 'var(--green)',
    error: 'var(--red)', warning: 'var(--yellow)'
  };
  const t = document.createElement('div');
  t.style.cssText = `
    background:var(--surface);border:1px solid var(--border2);
    border-left:3px solid ${colors[type] || colors.info};
    padding:12px 16px;border-radius:8px;font-size:13px;
    color:var(--text);font-family:var(--font);
    box-shadow:0 8px 32px rgba(0,0,0,.4);
    animation:slideIn .2s ease;max-width:320px;
  `;
  t.textContent = message;
  container.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(() => t.remove(), 300); }, duration);
};

// Inject animation keyframes once
(function() {
  if (document.getElementById('portal-keyframes')) return;
  const s = document.createElement('style');
  s.id = 'portal-keyframes';
  s.textContent = `@keyframes slideIn{from{transform:translateX(20px);opacity:0}to{transform:none;opacity:1}}`;
  document.head.appendChild(s);
})();

// ── Mobile sidebar toggle ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  const sidebar = document.querySelector('.sidebar');
  if (!sidebar) return;

  // Add hamburger if needed
  const topbar = document.querySelector('.topbar');
  if (topbar && window.innerWidth <= 768) {
    const ham = document.createElement('button');
    ham.innerHTML = '☰';
    ham.style.cssText = 'background:none;border:none;color:var(--text);font-size:18px;cursor:pointer;padding:4px 8px;margin-right:8px;';
    ham.onclick = () => sidebar.classList.toggle('open');
    topbar.prepend(ham);
  }

  // Close sidebar on outside click (mobile)
  document.addEventListener('click', function(e) {
    if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
      if (!sidebar.contains(e.target)) sidebar.classList.remove('open');
    }
  });
});

// ── Highlight active nav item ─────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(a => {
    const href = a.getAttribute('href');
    if (href && href !== '#' && path === href) {
      a.classList.add('active');
    } else if (href && href !== '/' && href !== '/dashboard' && path.startsWith(href)) {
      a.classList.add('active');
    }
  });
});

// ── Keyboard shortcut: / = focus search/input ────────────────
document.addEventListener('keydown', function(e) {
  if (e.key === '/' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA' && e.target.tagName !== 'SELECT') {
    e.preventDefault();
    const firstInput = document.querySelector('input[type="text"], input:not([type]), textarea');
    if (firstInput) { firstInput.focus(); firstInput.select(); }
  }
  if (e.key === 'Escape') {
    document.querySelectorAll('[data-modal]').forEach(m => m.style.display = 'none');
  }
});
