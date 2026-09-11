/**
 * Bibyutatsu BookStore - Client Application
 * Features:
 * - 5-Theme system (Dark, Light, Batman, Cyberpunk, Ocean) with Three.js particle canvas
 * - 3D Bookshelf showcase & realistic book cards
 * - Series & Author shelf navigation
 * - Ultra-fast dual-script transliteration & fuzzy search
 * - Multi-format download management (EPUB, KFX, PDF, MOBI)
 * - Infinite scroll / batch rendering & URL state synchronization
 */

(function () {
  'use strict';

  /* --------------------------------------------------------------------------
     1. THREE.JS AMBIENT PARTICLE BACKGROUND (from bibyutatsu.github.io)
     -------------------------------------------------------------------------- */
  (function initThreeHero() {
    const canvas = document.getElementById('hero-canvas');
    if (!canvas || typeof THREE === 'undefined') return;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1200);
    camera.position.z = 320;

    const N = window.innerWidth < 700 ? 50 : 90;
    const nodes = [];
    const nodeGeo = new THREE.SphereGeometry(1.8, 6, 6);
    for (let i = 0; i < N; i++) {
      const mat = new THREE.MeshBasicMaterial({
        color: i % 3 === 0 ? 0x8855ff : 0x00ccff,
        transparent: true,
        opacity: Math.random() * 0.5 + 0.3
      });
      const m = new THREE.Mesh(nodeGeo, mat);
      m.position.set(
        (Math.random() - 0.5) * 700,
        (Math.random() - 0.5) * 460,
        (Math.random() - 0.5) * 340
      );
      m.userData.vx = (Math.random() - 0.5) * 0.18;
      m.userData.vy = (Math.random() - 0.5) * 0.15;
      scene.add(m);
      nodes.push(m);
    }

    const MAX = 240;
    const lPos = new Float32Array(MAX * 6), lCol = new Float32Array(MAX * 6);
    const lGeo = new THREE.BufferGeometry();
    lGeo.setAttribute('position', new THREE.BufferAttribute(lPos, 3));
    lGeo.setAttribute('color', new THREE.BufferAttribute(lCol, 3));
    const lMat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.18 });
    const lines = new THREE.LineSegments(lGeo, lMat);
    scene.add(lines);

    const icoGeo = new THREE.IcosahedronGeometry(64, 1);
    const icoMat = new THREE.MeshBasicMaterial({ color: 0x00ccff, wireframe: true, transparent: true, opacity: 0.22 });
    const ico = new THREE.Mesh(icoGeo, icoMat);
    ico.position.set(window.innerWidth < 700 ? 0 : 260, 10, -60);
    scene.add(ico);

    const loader = new THREE.TextureLoader();
    const pGeo = new THREE.BufferGeometry();
    const pCount = 180;
    const pPos = new Float32Array(pCount * 3);
    for (let i = 0; i < pCount * 3; i++) pPos[i] = (Math.random() - 0.5) * 900;
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
    const pMat = new THREE.PointsMaterial({
      size: 0.5,
      color: 0xffffff,
      transparent: true,
      opacity: 0.7,
      alphaTest: 0.5,
      depthWrite: false
    });
    loader.load('assets/particles/bokeh.png', tex => {
      pMat.map = tex;
      pMat.needsUpdate = true;
    });
    const particles = new THREE.Points(pGeo, pMat);
    scene.add(particles);

    const THEME_COLORS = {
      dark:      { ico: 0x00ccff, n1: 0x00ccff, n2: 0x8855ff, p: 0xffffff, ptex: 'bokeh' },
      light:     { ico: 0x0055cc, n1: 0x0055cc, n2: 0x7722cc, p: 0x0055cc, ptex: 'bokeh' },
      batman:    { ico: 0xFFE919, n1: 0xFFE919, n2: 0xff4444, p: 0xFFE919, ptex: 'batman' },
      cyberpunk: { ico: 0xff0080, n1: 0xff0080, n2: 0x00ffcc, p: 0xff0080, ptex: 'bokeh' },
      ocean:     { ico: 0x00e5b0, n1: 0x00e5b0, n2: 0x0099ff, p: 0x00e5b0, ptex: 'bokeh' },
    };
    let lastTex = 'bokeh';

    window.updateThreeColors = function(theme) {
      const c = THEME_COLORS[theme] || THEME_COLORS.dark;
      icoMat.color.setHex(c.ico);
      nodes.forEach((n, i) => n.material.color.setHex(i % 3 === 0 ? c.n2 : c.n1));
      pMat.color.setHex(c.p);
      if (c.ptex !== lastTex) {
        lastTex = c.ptex;
        loader.load(`assets/particles/${c.ptex}.png`, tex => {
          pMat.map = tex;
          pMat.needsUpdate = true;
        });
      }
    };

    const cA = new THREE.Color(0x00ccff), cB = new THREE.Color(0x8855ff);
    function updateLines() {
      let cnt = 0;
      for (let i = 0; i < nodes.length && cnt < MAX; i++) {
        for (let j = i + 1; j < nodes.length && cnt < MAX; j++) {
          const dx = nodes[i].position.x - nodes[j].position.x;
          const dy = nodes[i].position.y - nodes[j].position.y;
          const dz = nodes[i].position.z - nodes[j].position.z;
          const d = Math.sqrt(dx * dx + dy * dy + dz * dz);
          if (d < 130) {
            const idx = cnt * 6, f = 1 - d / 130;
            const c = cnt % 2 === 0 ? cA : cB;
            lPos[idx]   = nodes[i].position.x; lPos[idx+1] = nodes[i].position.y; lPos[idx+2] = nodes[i].position.z;
            lPos[idx+3] = nodes[j].position.x; lPos[idx+4] = nodes[j].position.y; lPos[idx+5] = nodes[j].position.z;
            lCol[idx]   = c.r * f;             lCol[idx+1] = c.g * f;             lCol[idx+2] = c.b * f;
            lCol[idx+3] = c.r * f;             lCol[idx+4] = c.g * f;             lCol[idx+5] = c.b * f;
            cnt++;
          }
        }
      }
      lGeo.setDrawRange(0, cnt * 2);
      lGeo.attributes.position.needsUpdate = true;
      lGeo.attributes.color.needsUpdate = true;
    }

    let mx = 0, my = 0, tx = 0, ty = 0;
    document.addEventListener('mousemove', e => {
      mx = (e.clientX / window.innerWidth - 0.5) * 2;
      my = (e.clientY / window.innerHeight - 0.5) * 2;
    });

    window.addEventListener('resize', () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });

    let frame = 0, heroGone = false;
    window.addEventListener('scroll', () => {
      heroGone = window.scrollY > window.innerHeight * 1.2;
      canvas.style.opacity = heroGone ? '0' : '1';
    });

    function animate() {
      requestAnimationFrame(animate);
      if (heroGone) return;
      frame++;

      nodes.forEach(n => {
        n.position.x += n.userData.vx;
        n.position.y += n.userData.vy;
        if (Math.abs(n.position.x) > 360) n.userData.vx *= -1;
        if (Math.abs(n.position.y) > 240) n.userData.vy *= -1;
      });

      tx += (mx * 18 - tx) * 0.03;
      ty += (my * 10 - ty) * 0.03;
      camera.position.x = tx;
      camera.position.y = -ty;
      camera.lookAt(scene.position);

      ico.rotation.y += 0.05 * (mx * 0.5 - ico.rotation.y);
      ico.rotation.x += 0.05 * (my * 0.5 - ico.rotation.x);
      ico.rotation.z += 0.002;

      particles.rotation.y = -mx * 0.0002;
      particles.rotation.x = -my * 0.0002;

      if (frame % 4 === 0) updateLines();
      renderer.render(scene, camera);
    }
    animate();
  })();

  /* --------------------------------------------------------------------------
     2. CUSTOM CURSOR & MAGNETIC BUTTONS
     -------------------------------------------------------------------------- */
  (function initCursorAndMagnetic() {
    if (window.matchMedia('(hover: none)').matches) return;
    const dot = document.getElementById('cursor-dot');
    const ring = document.getElementById('cursor-ring');
    if (!dot || !ring) return;

    let mx = 0, my = 0, rx = 0, ry = 0;
    document.addEventListener('mousemove', e => {
      mx = e.clientX;
      my = e.clientY;
      dot.style.left = mx + 'px';
      dot.style.top = my + 'px';
    });

    const hoverSelector = 'a, button, .book-card, .tag-btn, .pill, .format-btn, .series-card, .author-chip, .book-3d-item, .social-btn, .theme-opt, select';
    document.addEventListener('mouseover', e => {
      if (e.target.closest(hoverSelector)) document.body.classList.add('c-hover');
    });
    document.addEventListener('mouseout', e => {
      if (e.target.closest(hoverSelector)) document.body.classList.remove('c-hover');
    });
    document.addEventListener('mousedown', () => document.body.classList.add('c-click'));
    document.addEventListener('mouseup', () => document.body.classList.remove('c-click'));

    (function lerpRing() {
      rx += (mx - rx) * 0.15;
      ry += (my - ry) * 0.15;
      ring.style.left = rx + 'px';
      ring.style.top = ry + 'px';
      requestAnimationFrame(lerpRing);
    })();

    window.applyMagnetic = function(selector) {
      document.querySelectorAll(selector).forEach(btn => {
        btn.addEventListener('mouseenter', () => btn.style.transition = 'transform 0.1s linear');
        btn.addEventListener('mousemove', e => {
          const r = btn.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
          btn.style.transform = `translate(${(e.clientX - cx) * 0.24}px, ${(e.clientY - cy) * 0.24}px)`;
        });
        btn.addEventListener('mouseleave', () => {
          btn.style.transition = 'transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
          btn.style.transform = '';
        });
      });
    };
    window.applyMagnetic('.btn-primary, .btn-ghost, .social-btn, .theme-opt, .tag-btn');
  })();

  /* --------------------------------------------------------------------------
     3. 3D CARD TILT
     -------------------------------------------------------------------------- */
  window.applyTilt = function(selector) {
    if (window.matchMedia('(hover: none)').matches) return;
    document.querySelectorAll(selector).forEach(card => {
      if (card.dataset.tiltInit) return;
      card.dataset.tiltInit = 'true';
      card.addEventListener('mouseenter', () => card.style.transition = 'transform 0.1s linear');
      card.addEventListener('mousemove', e => {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        card.style.transform = `perspective(700px) rotateX(${y * -7}deg) rotateY(${x * 7}deg) translateY(-5px)`;
      });
      card.addEventListener('mouseleave', () => {
        card.style.transition = 'transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
        card.style.transform = '';
      });
    });
  };

  /* --------------------------------------------------------------------------
     4. 5-THEME ENGINE (from bibyutatsu.github.io)
     -------------------------------------------------------------------------- */
  (function initThemeEngine() {
    const btn = document.getElementById('theme-btn');
    const pop = document.getElementById('theme-popover');
    const opts = document.querySelectorAll('.theme-opt');
    if (!btn || !pop) return;

    const saved = localStorage.getItem('bm-theme') || 'dark';
    applyTheme(saved, false);

    btn.addEventListener('click', e => {
      e.stopPropagation();
      pop.classList.toggle('open');
    });

    document.addEventListener('click', e => {
      if (!btn.contains(e.target)) pop.classList.remove('open');
    });
    pop.addEventListener('click', e => e.stopPropagation());

    opts.forEach(opt => {
      opt.addEventListener('click', () => {
        applyTheme(opt.dataset.theme, true);
        pop.classList.remove('open');
      });
    });

    function applyTheme(theme, save) {
      document.documentElement.setAttribute('data-theme', theme);
      if (save) localStorage.setItem('bm-theme', theme);
      opts.forEach(o => o.classList.toggle('active', o.dataset.theme === theme));

      const names = { dark: 'Dark', light: 'Light', batman: 'Batman', cyberpunk: 'Cyber', ocean: 'Ocean' };
      const label = btn.querySelector('.theme-label');
      if (label) label.textContent = names[theme] || theme;

      if (typeof window.updateThreeColors === 'function') {
        window.updateThreeColors(theme);
      }
    }
  })();

  /* --------------------------------------------------------------------------
     5. NAVIGATION & SCROLL
     -------------------------------------------------------------------------- */
  (function initNavAndScroll() {
    const nav = document.getElementById('nav');
    const toggle = document.getElementById('menu-toggle');
    const links = document.querySelector('.nav-links');

    window.addEventListener('scroll', () => {
      if (nav) nav.classList.toggle('scrolled', window.scrollY > 40);

      const progressBar = document.getElementById('progress-bar');
      if (progressBar && !CSS.supports('animation-timeline', 'scroll()')) {
        const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
        const progress = (window.scrollY / totalHeight) * 100;
        progressBar.style.width = `${progress}%`;
      }
    });

    if (toggle && links) {
      toggle.addEventListener('click', () => {
        links.classList.toggle('open');
        document.body.classList.toggle('menu-open');
      });
      links.querySelectorAll('a').forEach(a => {
        a.addEventListener('click', () => {
          links.classList.remove('open');
          document.body.classList.remove('menu-open');
        });
      });
    }
  })();

  /* --------------------------------------------------------------------------
     6. APPLICATION STATE & CATALOG ENGINE
     -------------------------------------------------------------------------- */
  const state = {
    catalog: null,
    books: [],
    filteredBooks: [],
    renderedCount: 0,
    pageSize: 24,
    currentQuery: '',
    selectedGenre: 'all',
    selectedFormat: 'all',
    selectedAuthor: 'all',
    selectedSort: 'popular',
    topAuthors: [],
    genres: []
  };

  const elements = {
    searchInput: document.getElementById('search-input'),
    clearSearch: document.getElementById('clear-search'),
    quickTags: document.getElementById('quick-tags'),
    genrePills: document.getElementById('genre-pills'),
    formatPills: document.getElementById('format-pills'),
    authorFilter: document.getElementById('author-filter'),
    sortSelect: document.getElementById('sort-select'),
    resultsCount: document.getElementById('results-count'),
    resetFiltersBtn: document.getElementById('reset-filters-btn'),
    booksGrid: document.getElementById('books-grid'),
    emptyState: document.getElementById('empty-state'),
    emptyResetBtn: document.getElementById('empty-reset-btn'),
    loadMoreContainer: document.getElementById('load-more-container'),
    loadMoreBtn: document.getElementById('load-more-btn'),
    modalOverlay: document.getElementById('book-modal-overlay'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
    modalBody: document.getElementById('modal-body'),
    statCountText: document.getElementById('stat-count-text')
  };

  /* --------------------------------------------------------------------------
     Fuzzy Search Engine & Levenshtein Distance
     -------------------------------------------------------------------------- */
  function levenshtein(s1, s2) {
    if (s1.length < s2.length) return levenshtein(s2, s1);
    if (s2.length === 0) return s1.length;

    let prevRow = [];
    for (let i = 0; i <= s2.length; i++) prevRow[i] = i;

    for (let i = 0; i < s1.length; i++) {
      const currRow = [i + 1];
      for (let j = 0; j < s2.length; j++) {
        const cost = s1[i] === s2[j] ? 0 : 1;
        currRow.push(Math.min(currRow[j] + 1, prevRow[j + 1] + 1, prevRow[j] + cost));
      }
      prevRow = currRow;
    }
    return prevRow[s2.length];
  }

  function matchesToken(qTok, targetTokens, maxDist = 2) {
    for (let i = 0; i < targetTokens.length; i++) {
      const t = targetTokens[i];
      if (t.includes(qTok) || t.startsWith(qTok)) return true;
      if (qTok.length >= 4 && Math.abs(qTok.length - t.length) <= maxDist) {
        if (levenshtein(qTok, t) <= maxDist) return true;
      }
    }
    return false;
  }

  /* --------------------------------------------------------------------------
     Catalog Loading & Setup
     -------------------------------------------------------------------------- */
  async function loadCatalog() {
    try {
      const response = await fetch('./catalog.json');
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      state.catalog = data;
      state.books = data.books || [];
      state.topAuthors = data.top_authors || [];
      state.genres = data.genres || [];

      if (elements.statCountText && data.stats) {
        elements.statCountText.textContent = `${data.stats.total_books.toLocaleString()} Books`;
      }

      setupFiltersUI();
      setupSpotlights();
      parseUrlParams();
      applyFiltersAndSearch();
    } catch (err) {
      console.error('Failed to load catalog:', err);
      elements.booksGrid.innerHTML = `
        <div class="empty-state" style="display: block; grid-column: 1 / -1;">
          <div class="empty-icon">⚠️</div>
          <h3>Failed to load ebook catalog</h3>
          <p>Please check your connection or make sure catalog.json is present.</p>
        </div>
      `;
    }
  }

  function setupFiltersUI() {
    // 1. Department / Genre Pills
    if (state.genres.length > 0) {
      const frag = document.createDocumentFragment();
      state.genres.slice(0, 10).forEach(g => {
        const btn = document.createElement('button');
        btn.className = 'pill';
        btn.dataset.genre = g.genre;
        const cleanName = g.genre.split('(')[0].trim();
        btn.textContent = `${cleanName} (${g.count})`;
        frag.appendChild(btn);
      });
      elements.genrePills.appendChild(frag);
    }

    // 2. Author Select Dropdown
    if (state.topAuthors.length > 0) {
      const frag = document.createDocumentFragment();
      state.topAuthors.forEach(a => {
        const opt = document.createElement('option');
        opt.value = a.author;
        opt.textContent = `${a.author} (${a.author_en}) [${a.count}]`;
        frag.appendChild(opt);
      });
      elements.authorFilter.appendChild(frag);
    }

    if (window.applyMagnetic) {
      window.applyMagnetic('.pill, .format-btn');
    }
  }

  /* --------------------------------------------------------------------------
     Bookstore Spotlight & Showcase Interactions
     -------------------------------------------------------------------------- */
  function setupSpotlights() {
    // 1. 3D Showcase Books
    document.querySelectorAll('.book-3d-item').forEach(item => {
      item.addEventListener('click', () => {
        const bookId = item.dataset.bookId;
        const targetBook = state.books.find(b => b.id === bookId);
        if (targetBook) {
          openBookModal(targetBook);
        } else {
          // Fallback: search by title
          const title = item.getAttribute('title') || '';
          elements.searchInput.value = title.split('(')[0].trim();
          state.currentQuery = elements.searchInput.value;
          applyFiltersAndSearch();
          scrollToCatalog();
        }
      });
    });

    // 2. Series Shelf Cards
    document.querySelectorAll('.series-card').forEach(card => {
      card.addEventListener('click', () => {
        const term = card.dataset.search;
        elements.searchInput.value = term;
        state.currentQuery = term;
        elements.clearSearch.style.display = 'flex';
        applyFiltersAndSearch();
        scrollToCatalog();
      });
    });

    // 3. Authors Spotlight Chips
    document.querySelectorAll('.author-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const author = chip.dataset.author;
        state.selectedAuthor = author;
        elements.authorFilter.value = author;
        applyFiltersAndSearch();
        scrollToCatalog();
      });
    });

    if (window.applyTilt) {
      window.applyTilt('.series-card, .author-chip');
    }
  }

  function scrollToCatalog() {
    const section = document.getElementById('catalog-section');
    if (section) {
      section.scrollIntoView({ behavior: 'smooth' });
    }
  }

  /* --------------------------------------------------------------------------
     URL Parameter Sync
     -------------------------------------------------------------------------- */
  function parseUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const q = params.get('q');
    const genre = params.get('genre');
    const author = params.get('author');
    const format = params.get('format');
    const sort = params.get('sort');

    if (q) {
      state.currentQuery = q;
      elements.searchInput.value = q;
      elements.clearSearch.style.display = 'flex';
    }
    if (genre) state.selectedGenre = genre;
    if (author) state.selectedAuthor = author;
    if (format) state.selectedFormat = format;
    if (sort) state.selectedSort = sort;

    syncFilterControlsUI();
  }

  function updateUrlParams() {
    const params = new URLSearchParams();
    if (state.currentQuery) params.set('q', state.currentQuery);
    if (state.selectedGenre !== 'all') params.set('genre', state.selectedGenre);
    if (state.selectedAuthor !== 'all') params.set('author', state.selectedAuthor);
    if (state.selectedFormat !== 'all') params.set('format', state.selectedFormat);
    if (state.selectedSort !== 'popular') params.set('sort', state.selectedSort);

    const newUrl = params.toString() ? `${window.location.pathname}?${params.toString()}` : window.location.pathname;
    window.history.replaceState({}, '', newUrl);
  }

  function syncFilterControlsUI() {
    const genreButtons = elements.genrePills.querySelectorAll('.pill');
    genreButtons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.genre === state.selectedGenre);
    });

    const formatButtons = elements.formatPills.querySelectorAll('.format-btn');
    formatButtons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.format === state.selectedFormat);
    });

    elements.authorFilter.value = state.selectedAuthor;
    elements.sortSelect.value = state.selectedSort;
  }

  /* --------------------------------------------------------------------------
     Search & Filtering Logic
     -------------------------------------------------------------------------- */
  function applyFiltersAndSearch() {
    const query = state.currentQuery.trim().toLowerCase();
    const queryTokens = query.split(/\s+/).filter(Boolean);

    let filtered = state.books.filter(book => {
      // Search Query
      if (queryTokens.length > 0) {
        const searchTokens = (book.search_text || '').toLowerCase().split(/\s+/);
        const matchesAll = queryTokens.every(qTok => matchesToken(qTok, searchTokens, 2));
        if (!matchesAll) return false;
      }

      // Genre
      if (state.selectedGenre !== 'all') {
        const hasGenre = book.genres.some(g => g.toLowerCase().includes(state.selectedGenre.toLowerCase()));
        if (!hasGenre) return false;
      }

      // Format
      if (state.selectedFormat !== 'all') {
        if (!book.formats || !book.formats[state.selectedFormat]) return false;
      }

      // Author
      if (state.selectedAuthor !== 'all') {
        if (book.author !== state.selectedAuthor) return false;
      }

      return true;
    });

    filtered = sortBooks(filtered, state.selectedSort);

    state.filteredBooks = filtered;
    state.renderedCount = 0;
    elements.booksGrid.innerHTML = '';

    elements.resultsCount.innerHTML = `Showing <strong>${filtered.length.toLocaleString()}</strong> books`;
    const hasActiveFilters = query || state.selectedGenre !== 'all' || state.selectedFormat !== 'all' || state.selectedAuthor !== 'all';
    elements.resetFiltersBtn.style.display = hasActiveFilters ? 'inline-block' : 'none';

    if (filtered.length === 0) {
      elements.emptyState.style.display = 'block';
      elements.loadMoreContainer.style.display = 'none';
    } else {
      elements.emptyState.style.display = 'none';
      renderNextBatch();
    }

    updateUrlParams();
  }

  function sortBooks(books, sortMethod) {
    const list = [...books];
    switch (sortMethod) {
      case 'title-asc':
        return list.sort((a, b) => a.title.localeCompare(b.title, 'bn'));
      case 'title-en-asc':
        return list.sort((a, b) => a.title_en.localeCompare(b.title_en));
      case 'author-asc':
        return list.sort((a, b) => a.author_en.localeCompare(b.author_en));
      case 'popular':
      default:
        return list;
    }
  }

  /* --------------------------------------------------------------------------
     Batch Rendering & Card Creation (3D Bookstore Book Design)
     -------------------------------------------------------------------------- */
  function renderNextBatch() {
    const nextBatch = state.filteredBooks.slice(state.renderedCount, state.renderedCount + state.pageSize);
    if (nextBatch.length === 0) {
      elements.loadMoreContainer.style.display = 'none';
      return;
    }

    const frag = document.createDocumentFragment();
    nextBatch.forEach(book => {
      frag.appendChild(createBookCard(book));
    });

    elements.booksGrid.appendChild(frag);
    state.renderedCount += nextBatch.length;

    if (state.renderedCount < state.filteredBooks.length) {
      elements.loadMoreContainer.style.display = 'flex';
    } else {
      elements.loadMoreContainer.style.display = 'none';
    }

    if (window.applyTilt) {
      window.applyTilt('.book-card');
    }
    if (window.applyMagnetic) {
      window.applyMagnetic('.download-btn, .details-btn');
    }
  }

  function createBookCard(book) {
    const card = document.createElement('article');
    card.className = 'book-card';
    card.dataset.id = book.id;

    const seriesHtml = book.series ? `<span class="series-tag">${escapeHtml(book.series.name_bn)}</span>` : '<span></span>';
    
    let formatBadgesHtml = '';
    const fmts = Object.keys(book.formats || {});
    fmts.forEach(f => {
      formatBadgesHtml += `<span class="badge-fmt ${f}">${f.toUpperCase()}</span>`;
    });

    const primaryFormat = book.formats.epub ? 'epub' : (book.formats.kfx ? 'kfx' : fmts[0]);
    const primaryInfo = book.formats[primaryFormat] || {};
    const downloadHref = primaryInfo.download_url || '#';
    const downloadFilename = primaryInfo.filename || `${book.id}.${primaryFormat}`;

    let coverHtml = '';
    if (book.cover) {
      coverHtml = `<img src="${book.cover}" alt="${escapeHtml(book.title)}" class="book-cover" loading="lazy">`;
    } else {
      coverHtml = `
        <div class="cover-fallback">
          <span class="cover-fallback-icon">📖</span>
          <span class="cover-fallback-title">${escapeHtml(book.title)}</span>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="book-cover-wrap">
        ${coverHtml}
        <div class="card-badges">
          ${seriesHtml}
          <div class="format-tags-list">
            ${formatBadgesHtml}
          </div>
        </div>
      </div>
      <div class="book-info">
        <h3 class="book-title" title="${escapeHtml(book.title)}">${escapeHtml(book.title)}</h3>
        <span class="book-title-en" title="${escapeHtml(book.title_en)}">${escapeHtml(book.title_en)}</span>
        <div class="book-author" title="${escapeHtml(book.author)} (${escapeHtml(book.author_en)})">
          ${escapeHtml(book.author)}
        </div>
        <div class="card-actions">
          <a href="${downloadHref}" download="${downloadFilename}" class="download-btn" data-fmt="${primaryFormat}" title="Download ${primaryFormat.toUpperCase()} (${primaryInfo.size_formatted || ''})">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            <span>${primaryFormat.toUpperCase()}</span>
          </a>
          <button class="details-btn" aria-label="Book Details">Details</button>
        </div>
      </div>
    `;

    card.addEventListener('click', (e) => {
      if (e.target.closest('.download-btn')) {
        handleDownloadClick(e, book, primaryFormat, primaryInfo);
        return;
      }
      openBookModal(book);
    });

    return card;
  }

  function handleDownloadClick(e, book, format, formatInfo) {
    if (!formatInfo.download_url || formatInfo.download_url === '#') {
      e.preventDefault();
      openBookModal(book);
    }
  }

  /* --------------------------------------------------------------------------
     Book Detail Modal
     -------------------------------------------------------------------------- */
  function openBookModal(book) {
    const fmts = Object.entries(book.formats || {});
    let downloadCardsHtml = '';

    fmts.forEach(([fmtKey, fmtInfo]) => {
      const dlUrl = fmtInfo.download_url || '#';
      const targetAttr = fmtInfo.download_url ? 'target="_blank" rel="noopener"' : '';
      downloadCardsHtml += `
        <a href="${dlUrl}" download="${fmtInfo.filename}" ${targetAttr} class="modal-dl-card">
          <span class="modal-dl-format">${fmtKey.toUpperCase()}</span>
          <span class="modal-dl-size">${fmtInfo.size_formatted}</span>
          <span class="modal-dl-btn">Download ↗</span>
        </a>
      `;
    });

    const seriesBadge = book.series ? `<span class="modal-series-badge">সিরিজ: ${escapeHtml(book.series.name_bn)} (${escapeHtml(book.series.name_en)})</span>` : '';
    
    let genresHtml = '';
    (book.genres || []).forEach(g => {
      genresHtml += `<span class="modal-genre-tag">${escapeHtml(g)}</span>`;
    });

    const coverHtml = book.cover 
      ? `<img src="${book.cover}" alt="${escapeHtml(book.title)}" class="modal-cover">`
      : `<div class="cover-fallback"><span class="cover-fallback-icon">📖</span></div>`;

    const descriptionHtml = book.description 
      ? `<div class="modal-desc">${escapeHtml(book.description)}</div>`
      : `<div class="modal-desc" style="color: var(--text-muted); font-style: italic;">No synopsis available for this volume.</div>`;

    elements.modalBody.innerHTML = `
      <div class="modal-cover-wrap">
        ${coverHtml}
      </div>
      <div class="modal-info">
        <h2 class="modal-title">${escapeHtml(book.title)}</h2>
        <div class="modal-title-en">${escapeHtml(book.title_en)}</div>
        <div class="modal-meta-row">
          <span class="modal-author-link" data-author="${escapeHtml(book.author)}">
            লেখক: ${escapeHtml(book.author)} (${escapeHtml(book.author_en)})
          </span>
          ${seriesBadge}
          ${book.year ? `<span class="modal-year-badge">Year: ${book.year}</span>` : ''}
        </div>
        <div class="modal-genres">
          ${genresHtml}
        </div>
        ${descriptionHtml}
        <div class="modal-downloads-section">
          <h4>Available Formats</h4>
          <div class="modal-download-grid">
            ${downloadCardsHtml}
          </div>
        </div>
      </div>
    `;

    const authorLink = elements.modalBody.querySelector('.modal-author-link');
    if (authorLink) {
      authorLink.addEventListener('click', () => {
        closeModal();
        state.selectedAuthor = book.author;
        syncFilterControlsUI();
        applyFiltersAndSearch();
        scrollToCatalog();
      });
    }

    elements.modalOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';

    if (window.applyMagnetic) {
      window.applyMagnetic('.modal-dl-card, .modal-close');
    }
  }

  function closeModal() {
    elements.modalOverlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  /* --------------------------------------------------------------------------
     Event Listeners
     -------------------------------------------------------------------------- */
  function setupEvents() {
    let debounceTimer;
    elements.searchInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      const val = e.target.value;
      elements.clearSearch.style.display = val ? 'flex' : 'none';

      debounceTimer = setTimeout(() => {
        state.currentQuery = val;
        applyFiltersAndSearch();
      }, 150);
    });

    elements.clearSearch.addEventListener('click', () => {
      elements.searchInput.value = '';
      state.currentQuery = '';
      elements.clearSearch.style.display = 'none';
      applyFiltersAndSearch();
      elements.searchInput.focus();
    });

    elements.quickTags.addEventListener('click', (e) => {
      const btn = e.target.closest('.tag-btn');
      if (!btn) return;
      const term = btn.dataset.search;
      elements.searchInput.value = term;
      state.currentQuery = term;
      elements.clearSearch.style.display = 'flex';
      applyFiltersAndSearch();
      scrollToCatalog();
    });

    elements.genrePills.addEventListener('click', (e) => {
      const pill = e.target.closest('.pill');
      if (!pill) return;
      state.selectedGenre = pill.dataset.genre;
      syncFilterControlsUI();
      applyFiltersAndSearch();
    });

    elements.formatPills.addEventListener('click', (e) => {
      const btn = e.target.closest('.format-btn');
      if (!btn) return;
      state.selectedFormat = btn.dataset.format;
      syncFilterControlsUI();
      applyFiltersAndSearch();
    });

    elements.authorFilter.addEventListener('change', (e) => {
      state.selectedAuthor = e.target.value;
      applyFiltersAndSearch();
    });

    elements.sortSelect.addEventListener('change', (e) => {
      state.selectedSort = e.target.value;
      applyFiltersAndSearch();
    });

    elements.resetFiltersBtn.addEventListener('click', resetAllFilters);
    elements.emptyResetBtn.addEventListener('click', resetAllFilters);

    elements.loadMoreBtn.addEventListener('click', () => {
      renderNextBatch();
    });

    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && state.renderedCount < state.filteredBooks.length) {
          renderNextBatch();
        }
      }, { rootMargin: '400px' });
      observer.observe(elements.loadMoreContainer);
    }

    elements.modalCloseBtn.addEventListener('click', closeModal);
    elements.modalOverlay.addEventListener('click', (e) => {
      if (e.target === elements.modalOverlay) closeModal();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeModal();
    });
  }

  function resetAllFilters() {
    state.currentQuery = '';
    state.selectedGenre = 'all';
    state.selectedFormat = 'all';
    state.selectedAuthor = 'all';
    state.selectedSort = 'popular';

    elements.searchInput.value = '';
    elements.clearSearch.style.display = 'none';

    syncFilterControlsUI();
    applyFiltersAndSearch();
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.toString()
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Initialize
  setupEvents();
  loadCatalog();

})();
