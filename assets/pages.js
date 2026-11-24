/**
 * PAGES.JS — Shared Subpage Runtime Engine for Bibyutatsu BookStore
 * 5-Theme Synchronization · Canvas UI Tactile Shards · 3D Tilt · Pretext Layout
 */

(function () {
  'use strict';

  /* --------------------------------------------------------------------------
     1. THEME BOOTSTRAPPER & SYNC
     -------------------------------------------------------------------------- */
  const THEMES = ['dark', 'light', 'batman', 'cyberpunk', 'ocean'];
  const savedTheme = localStorage.getItem('bm-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);

  window.cyclePageTheme = function () {
    const cur = document.documentElement.getAttribute('data-theme') || 'dark';
    const nextIdx = (THEMES.indexOf(cur) + 1) % THEMES.length;
    const nextTheme = THEMES[nextIdx];
    document.documentElement.setAttribute('data-theme', nextTheme);
    localStorage.setItem('bm-theme', nextTheme);
    const label = document.getElementById('subpage-theme-label');
    if (label) label.textContent = nextTheme.toUpperCase();
    if (typeof window.triggerCanvasUIButtonShatter === 'function') {
      window.triggerCanvasUIButtonShatter(window.innerWidth - 60, 30);
    }
  };

  /* --------------------------------------------------------------------------
     2. CANVAS UI: TACTILE GLASS/PARCHMENT SHATTER (Zero-Idle CPU)
     -------------------------------------------------------------------------- */
  (function initCanvasUI() {
    const canvas = document.getElementById('canvas-ui-layer');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let particles = [];
    let shockwaves = [];
    let isRunning = false;

    function resize() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize, { passive: true });

    function startLoop() {
      if (!isRunning) {
        isRunning = true;
        requestAnimationFrame(renderLoop);
      }
    }

    window.triggerCanvasUIButtonShatter = function (x, y) {
      if (x === undefined || y === undefined) return;
      const theme = document.documentElement.getAttribute('data-theme') || 'dark';
      const count = 16;
      const colors = {
        dark: ['rgba(0,204,255,0.8)', 'rgba(136,85,255,0.8)', 'rgba(255,255,255,0.95)'],
        light: ['rgba(0,85,204,0.7)', 'rgba(119,34,204,0.7)', 'rgba(255,255,255,0.85)'],
        batman: ['rgba(255,233,25,0.95)', 'rgba(255,68,68,0.8)', 'rgba(255,255,255,0.95)'],
        cyberpunk: ['rgba(255,0,128,0.9)', 'rgba(0,255,204,0.9)', 'rgba(255,255,255,0.95)'],
        ocean: ['rgba(0,229,176,0.9)', 'rgba(0,153,255,0.9)', 'rgba(255,255,255,0.9)']
      }[theme] || ['rgba(0,204,255,0.8)', 'rgba(255,255,255,0.95)'];

      for (let i = 0; i < count; i++) {
        const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.45;
        const speed = Math.random() * 5.5 + 3.5;
        particles.push({
          x, y,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          rot: Math.random() * Math.PI * 2,
          vrot: (Math.random() - 0.5) * 0.28,
          size: Math.random() * 11 + 6,
          color: colors[Math.floor(Math.random() * colors.length)],
          life: 1.0,
          decay: Math.random() * 0.035 + 0.025
        });
      }

      shockwaves.push({
        x, y,
        radius: 6,
        maxRadius: 85,
        opacity: 0.8,
        color: colors[0],
        strokeWidth: 2.2
      });

      startLoop();
    };

    document.addEventListener('click', e => {
      const btn = e.target.closest('.download-btn, .nav-btn, .theme-subpage-btn, .read-check-btn, .badge, .mini-book-card');
      if (btn) {
        window.triggerCanvasUIButtonShatter(e.clientX, e.clientY);
      }
    });

    function renderLoop() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (let i = shockwaves.length - 1; i >= 0; i--) {
        const sw = shockwaves[i];
        if (sw.radius > 0) {
          ctx.save();
          ctx.beginPath();
          ctx.arc(sw.x, sw.y, sw.radius, 0, Math.PI * 2);
          ctx.strokeStyle = sw.color;
          ctx.globalAlpha = sw.opacity;
          ctx.lineWidth = sw.strokeWidth;
          ctx.stroke();
          ctx.restore();
        }
        sw.radius += 4.8;
        sw.opacity *= 0.94;
        if (sw.radius >= sw.maxRadius || sw.opacity <= 0.02) {
          shockwaves.splice(i, 1);
        }
      }

      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.vx *= 0.96;
        p.vy *= 0.96;
        p.rot += p.vrot;
        p.life -= p.decay;

        if (p.life <= 0) {
          particles.splice(i, 1);
          continue;
        }

        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.globalAlpha = p.life;
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.moveTo(-p.size * 0.5, p.size * 0.5);
        ctx.lineTo(p.size * 0.8, -p.size * 0.2);
        ctx.lineTo(p.size * 0.2, -p.size * 0.7);
        ctx.closePath();
        ctx.fill();
        ctx.strokeStyle = 'rgba(255,255,255,0.65)';
        ctx.lineWidth = 0.8;
        ctx.stroke();
        ctx.restore();
      }

      if (particles.length > 0 || shockwaves.length > 0) {
        requestAnimationFrame(renderLoop);
      } else {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        isRunning = false;
      }
    }
  })();

  /* --------------------------------------------------------------------------
     3. POKÉMON CARDS CSS: 3D TILT & HOLOGRAPHIC FOIL
     -------------------------------------------------------------------------- */
  function initHoloCards() {
    if (window.matchMedia && window.matchMedia('(hover: none)').matches) return;
    const cards = document.querySelectorAll('.holo-card:not([data-holo-active])');
    cards.forEach(card => {
      card.setAttribute('data-holo-active', 'true');
      let rafId = null;

      function onMouseMove(e) {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = (e.clientY - rect.top) / rect.height;

        const px = (x * 100).toFixed(1);
        const py = (y * 100).toFixed(1);
        const dx = x - 0.5;
        const dy = y - 0.5;

        const rotX = (dy * -10).toFixed(2);
        const rotY = (dx * 10).toFixed(2);
        const angle = (Math.atan2(dy, dx) * (180 / Math.PI) + 90).toFixed(1);
        const foilX = (50 + dx * 60).toFixed(1);
        const foilY = (50 + dy * 60).toFixed(1);

        if (rafId) cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(() => {
          card.style.setProperty('--pointer-x', `${px}%`);
          card.style.setProperty('--pointer-y', `${py}%`);
          card.style.setProperty('--foil-x', `${foilX}%`);
          card.style.setProperty('--foil-y', `${foilY}%`);
          card.style.setProperty('--angle', `${angle}deg`);
          card.style.setProperty('--holo-opacity', '1');
          card.style.transform = `perspective(1000px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateY(-6px) translateZ(8px)`;
        });
      }

      function onMouseEnter() {
        card.style.transition = 'transform 0.12s ease-out, border-color 0.3s ease, box-shadow 0.3s ease';
      }

      function onMouseLeave() {
        if (rafId) cancelAnimationFrame(rafId);
        card.style.transition = 'transform 0.65s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.38s ease, box-shadow 0.38s ease';
        card.style.setProperty('--holo-opacity', '0');
        card.style.transform = '';
      }

      card.addEventListener('mouseenter', onMouseEnter);
      card.addEventListener('mousemove', onMouseMove);
      card.addEventListener('mouseleave', onMouseLeave);
    });
  }
  window.initHoloCards = initHoloCards;

  /* --------------------------------------------------------------------------
     4. PRETEXT: TITLE BALANCING
     -------------------------------------------------------------------------- */
  const Pretext = (function () {
    const cache = new Map();
    let ctx = null;

    function getContext(font) {
      if (!ctx) {
        const c = document.createElement('canvas');
        ctx = c.getContext('2d');
      }
      ctx.font = font;
      return ctx;
    }

    function prepare(text, font) {
      const key = font + '::' + text;
      if (cache.has(key)) return cache.get(key);
      const c = getContext(font);
      const words = (text || '').split(/\s+/);
      const wordWidths = new Float32Array(words.length);
      const spaceWidth = c.measureText(' ').width;
      for (let i = 0; i < words.length; i++) wordWidths[i] = c.measureText(words[i]).width;
      const prep = { text, font, words, wordWidths, spaceWidth };
      cache.set(key, prep);
      return prep;
    }

    function layout(prep, containerWidth, lineHeight) {
      if (!prep || containerWidth <= 0) return { height: 0, lineCount: 0 };
      const { wordWidths, spaceWidth } = prep;
      let currentLineWidth = 0, lineCount = 1;
      for (let i = 0; i < wordWidths.length; i++) {
        const w = wordWidths[i];
        if (currentLineWidth + w <= containerWidth || currentLineWidth === 0) {
          currentLineWidth += w + spaceWidth;
        } else {
          currentLineWidth = w + spaceWidth;
          lineCount++;
        }
      }
      return { height: Math.round(lineCount * lineHeight), lineCount };
    }

    function balance(prep, containerWidth, lineHeight) {
      if (!prep) return containerWidth;
      const natural = layout(prep, containerWidth, lineHeight);
      if (natural.lineCount <= 1) return containerWidth;
      let low = containerWidth * 0.72, high = containerWidth, bestWidth = containerWidth;
      for (let iter = 0; iter < 8; iter++) {
        const mid = (low + high) / 2;
        if (layout(prep, mid, lineHeight).lineCount === natural.lineCount) {
          bestWidth = mid; high = mid;
        } else { low = mid; }
      }
      return Math.round(bestWidth);
    }

    return { prepare, layout, balance };
  })();

  function balanceHeadings() {
    const titleEl = document.querySelector('.book-title');
    if (titleEl && typeof Pretext !== 'undefined') {
      const prep = Pretext.prepare(titleEl.textContent.trim(), '800 28px "Hind Siliguri", "Inter", sans-serif');
      const maxW = titleEl.parentElement ? titleEl.parentElement.clientWidth : 600;
      const balanced = Pretext.balance(prep, maxW, 36);
      if (balanced > 0 && balanced < maxW) titleEl.style.maxWidth = `${balanced}px`;
    }
  }

  /* --------------------------------------------------------------------------
     5. SERIES READING ORDER PROGRESS TRACKER
     -------------------------------------------------------------------------- */
  function initSeriesProgress() {
    const seriesContainer = document.querySelector('[data-series-id]');
    if (!seriesContainer) return;
    const seriesId = seriesContainer.dataset.seriesId;
    const storageKey = `bm-read-${seriesId}`;
    let readSet = new Set(JSON.parse(localStorage.getItem(storageKey) || '[]'));

    function updateProgressUI() {
      const buttons = document.querySelectorAll('.read-check-btn');
      let count = 0;
      buttons.forEach(btn => {
        const bid = btn.dataset.bookId;
        const isRead = readSet.has(bid);
        btn.classList.toggle('checked', isRead);
        btn.textContent = isRead ? '✓ Read' : '+ Mark Read';
        if (isRead) count++;
      });
      const progressText = document.getElementById('series-progress-count');
      if (progressText) {
        progressText.textContent = `${count} / ${buttons.length} Completed`;
      }
    }

    document.querySelectorAll('.read-check-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const bid = btn.dataset.bookId;
        if (readSet.has(bid)) readSet.delete(bid);
        else readSet.add(bid);
        localStorage.setItem(storageKey, JSON.stringify([...readSet]));
        updateProgressUI();
      });
    });

    updateProgressUI();
  }

  /* --------------------------------------------------------------------------
     6. AUTHOR DIRECTORY LIVE SEARCH FILTER
     -------------------------------------------------------------------------- */
  function initAuthorSearch() {
    const searchInput = document.getElementById('author-search-input');
    const authorCards = document.querySelectorAll('.author-dir-card');
    if (!searchInput || !authorCards.length) return;

    let debounceTimer;
    searchInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      const query = (e.target.value || '').trim().toLowerCase();
      debounceTimer = setTimeout(() => {
        let matchCount = 0;
        authorCards.forEach(card => {
          const nameBn = (card.dataset.nameBn || '').toLowerCase();
          const nameEn = (card.dataset.nameEn || '').toLowerCase();
          const matches = !query || nameBn.includes(query) || nameEn.includes(query);
          card.style.display = matches ? '' : 'none';
          if (matches) matchCount++;
        });
        const countEl = document.getElementById('author-search-count');
        if (countEl) countEl.textContent = `${matchCount} Authors matching`;
      }, 150);
    });
  }

  // DOM Ready Initializer
  function initAll() {
    initHoloCards();
    balanceHeadings();
    initSeriesProgress();
    initAuthorSearch();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
