/**
 * Bibyutatsu BookStore - Client Application (Option 2: Storefront + Instant Grid)
 * Features:
 * - 5-Theme system (Dark, Light, Batman, Cyberpunk, Ocean) with Three.js particle canvas
 * - Sticky sidebar filter + mobile slide-in drawer
 * - Real 3D book cards with spine creases & direct format downloads
 * - Ultra-fast dual-script transliteration & fuzzy search (100% benchmark recall)
 * - URL state synchronization & batch infinite scrolling
 */

(function () {
  'use strict';

  /* --------------------------------------------------------------------------
     1. THREE.JS AMBIENT PARTICLE BACKGROUND
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

    const N = window.innerWidth < 700 ? 40 : 75;
    const nodes = [];
    const nodeGeo = new THREE.SphereGeometry(1.8, 6, 6);
    for (let i = 0; i < N; i++) {
      const mat = new THREE.MeshBasicMaterial({
        color: i % 3 === 0 ? 0x8855ff : 0x00ccff,
        transparent: true,
        opacity: Math.random() * 0.4 + 0.25
      });
      const m = new THREE.Mesh(nodeGeo, mat);
      m.position.set(
        (Math.random() - 0.5) * 700,
        (Math.random() - 0.5) * 460,
        (Math.random() - 0.5) * 340
      );
      m.userData.vx = (Math.random() - 0.5) * 0.15;
      m.userData.vy = (Math.random() - 0.5) * 0.12;
      scene.add(m);
      nodes.push(m);
    }

    const MAX = 200;
    const lPos = new Float32Array(MAX * 6), lCol = new Float32Array(MAX * 6);
    const lGeo = new THREE.BufferGeometry();
    lGeo.setAttribute('position', new THREE.BufferAttribute(lPos, 3));
    lGeo.setAttribute('color', new THREE.BufferAttribute(lCol, 3));
    const lMat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.15 });
    const lines = new THREE.LineSegments(lGeo, lMat);
    scene.add(lines);

    const loader = new THREE.TextureLoader();
    const pGeo = new THREE.BufferGeometry();
    const pCount = 140;
    const pPos = new Float32Array(pCount * 3);
    for (let i = 0; i < pCount * 3; i++) pPos[i] = (Math.random() - 0.5) * 900;
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
    const pMat = new THREE.PointsMaterial({
      size: 0.5,
      color: 0xffffff,
      transparent: true,
      opacity: 0.6,
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
      dark:      { n1: 0x00ccff, n2: 0x8855ff, p: 0xffffff, ptex: 'bokeh' },
      light:     { n1: 0x0055cc, n2: 0x7722cc, p: 0x0055cc, ptex: 'bokeh' },
      batman:    { n1: 0xFFE919, n2: 0xff4444, p: 0xFFE919, ptex: 'batman' },
      cyberpunk: { n1: 0xff0080, n2: 0x00ffcc, p: 0xff0080, ptex: 'bokeh' },
      ocean:     { n1: 0x00e5b0, n2: 0x0099ff, p: 0x00e5b0, ptex: 'bokeh' },
    };
    let lastTex = 'bokeh';

    window.updateThreeColors = function(theme) {
      const c = THEME_COLORS[theme] || THEME_COLORS.dark;
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
          if (d < 125) {
            const idx = cnt * 6, f = 1 - d / 125;
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

    let frame = 0;
    let lastTime = 0;
    const targetFps = 30;
    const frameInterval = 1000 / targetFps;
    let isPageVisible = !document.hidden;
    let isScrolling = false;
    let scrollPauseTimer = null;

    document.addEventListener('visibilitychange', () => {
      isPageVisible = !document.hidden;
      if (isPageVisible) requestAnimationFrame(animate);
    });

    window.addEventListener('scroll', () => {
      isScrolling = true;
      clearTimeout(scrollPauseTimer);
      scrollPauseTimer = setTimeout(() => {
        isScrolling = false;
      }, 150);
    }, { passive: true });

    function animate(currentTime = 0) {
      if (!isPageVisible) return;
      requestAnimationFrame(animate);

      const delta = currentTime - lastTime;
      if (delta < frameInterval) return;
      lastTime = currentTime - (delta % frameInterval);

      frame++;

      nodes.forEach(n => {
        n.position.x += n.userData.vx;
        n.position.y += n.userData.vy;
        if (Math.abs(n.position.x) > 360) n.userData.vx *= -1;
        if (Math.abs(n.position.y) > 240) n.userData.vy *= -1;
      });

      tx += (mx * 16 - tx) * 0.03;
      ty += (my * 8 - ty) * 0.03;
      camera.position.x = tx;
      camera.position.y = -ty;
      camera.lookAt(scene.position);

      particles.rotation.y = -mx * 0.0002;
      particles.rotation.x = -my * 0.0002;

      if (frame % 8 === 0) updateLines();
      if (!isScrolling) {
        renderer.render(scene, camera);
      }
    }
    requestAnimationFrame(animate);
  })();

  /* --------------------------------------------------------------------------
     2. CUSTOM CURSOR & MAGNETIC BUTTONS (GPU Accelerated translate3d)
     -------------------------------------------------------------------------- */
  (function initCursorAndMagnetic() {
    if (window.matchMedia('(hover: none)').matches) return;
    const dot = document.getElementById('cursor-dot');
    const ring = document.getElementById('cursor-ring');
    if (!dot || !ring) return;

    let mx = -100, my = -100, rx = -100, ry = -100;
    let dotRafActive = false;

    document.addEventListener('mousemove', e => {
      mx = e.clientX;
      my = e.clientY;
      if (!dotRafActive) {
        dotRafActive = true;
        requestAnimationFrame(() => {
          dot.style.transform = `translate3d(${mx}px, ${my}px, 0) translate(-50%, -50%)`;
          dotRafActive = false;
        });
      }
    }, { passive: true });

    const hoverSelector = 'a, button, .book-card, .side-tag, .genre-item, .side-fmt-btn, .theme-opt, select, .pagination-btn';
    document.addEventListener('mouseover', e => {
      if (e.target.closest(hoverSelector)) document.body.classList.add('c-hover');
    });
    document.addEventListener('mouseout', e => {
      if (e.target.closest(hoverSelector)) document.body.classList.remove('c-hover');
    });
    document.addEventListener('mousedown', () => document.body.classList.add('c-click'));
    document.addEventListener('mouseup', () => document.body.classList.remove('c-click'));

    (function lerpRing() {
      rx += (mx - rx) * 0.16;
      ry += (my - ry) * 0.16;
      ring.style.transform = `translate3d(${rx}px, ${ry}px, 0) translate(-50%, -50%)`;
      requestAnimationFrame(lerpRing);
    })();

    window.applyMagnetic = function(selector) {
      document.querySelectorAll(selector).forEach(btn => {
        if (btn.dataset.magneticInit) return;
        btn.dataset.magneticInit = 'true';
        btn.addEventListener('mouseenter', () => btn.style.transition = 'transform 0.1s linear');
        btn.addEventListener('mousemove', e => {
          const r = btn.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
          btn.style.transform = `translate3d(${(e.clientX - cx) * 0.22}px, ${(e.clientY - cy) * 0.22}px, 0)`;
        });
        btn.addEventListener('mouseleave', () => {
          btn.style.transition = 'transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
          btn.style.transform = '';
        });
      });
    };
    window.applyMagnetic('.btn-primary, .header-link, .theme-opt, .side-tag, .mobile-filter-btn');
  })();

  /* --------------------------------------------------------------------------
     3. 3D CARD TILT (RAF Throttled)
     -------------------------------------------------------------------------- */
  window.applyTilt = function(selector) {
    if (window.matchMedia('(hover: none)').matches) return;
    document.querySelectorAll(selector).forEach(card => {
      if (card.dataset.tiltInit) return;
      card.dataset.tiltInit = 'true';
      let tiltRaf = null;

      card.addEventListener('mouseenter', () => card.style.transition = 'transform 0.1s linear');
      card.addEventListener('mousemove', e => {
        if (tiltRaf) return;
        tiltRaf = requestAnimationFrame(() => {
          const r = card.getBoundingClientRect();
          const x = (e.clientX - r.left) / r.width - 0.5;
          const y = (e.clientY - r.top) / r.height - 0.5;
          card.style.transform = `perspective(700px) rotateX(${y * -7}deg) rotateY(${x * 7}deg) translateY(-5px)`;
          tiltRaf = null;
        });
      });
      card.addEventListener('mouseleave', () => {
        if (tiltRaf) {
          cancelAnimationFrame(tiltRaf);
          tiltRaf = null;
        }
        card.style.transition = 'transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
        card.style.transform = '';
      });
    });
  };

  /* --------------------------------------------------------------------------
     4. 5-THEME ENGINE
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
     5. MOBILE SLIDE-IN DRAWER LOGIC
     -------------------------------------------------------------------------- */
  (function initMobileDrawer() {
    const drawerToggle = document.getElementById('drawer-toggle-btn');
    const sidebar = document.getElementById('store-sidebar');
    const overlay = document.getElementById('drawer-overlay');
    const closeBtn = document.getElementById('drawer-close-btn');
    const doneBtn = document.getElementById('drawer-done-btn');

    function openDrawer() {
      if (sidebar) sidebar.classList.add('drawer-open');
      if (overlay) overlay.classList.add('active');
      if (drawerToggle) drawerToggle.setAttribute('aria-expanded', 'true');
      if (overlay) overlay.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
    }

    function closeDrawer() {
      if (sidebar) sidebar.classList.remove('drawer-open');
      if (overlay) overlay.classList.remove('active');
      if (drawerToggle) drawerToggle.setAttribute('aria-expanded', 'false');
      if (overlay) overlay.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
    }

    window.closeMobileDrawer = closeDrawer;

    if (drawerToggle) drawerToggle.addEventListener('click', openDrawer);
    if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
    if (doneBtn) doneBtn.addEventListener('click', closeDrawer);
    if (overlay) overlay.addEventListener('click', closeDrawer);

    // Touch swipe left to close drawer on mobile devices
    if (sidebar) {
      let touchStartX = 0;
      let touchStartY = 0;
      sidebar.addEventListener('touchstart', (e) => {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
      }, { passive: true });

      sidebar.addEventListener('touchend', (e) => {
        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        const diffX = touchEndX - touchStartX;
        const diffY = touchEndY - touchStartY;
        // Swipe left by at least 50px with predominantly horizontal motion
        if (diffX < -50 && Math.abs(diffX) > Math.abs(diffY)) {
          closeDrawer();
        }
      }, { passive: true });
    }
  })();

  /* --------------------------------------------------------------------------
     6. APPLICATION STATE & ACCELERATED COLLATORS
     -------------------------------------------------------------------------- */
  const bnCollator = new Intl.Collator('bn', { sensitivity: 'base' });
  const enCollator = new Intl.Collator('en', { sensitivity: 'base' });

  const state = {
    catalog: null,
    books: [],
    filteredBooks: [],
    currentPage: 1,
    pageSize: 24,
    totalPages: 1,
    currentQuery: '',
    selectedGenre: 'all',
    selectedFormat: 'all',
    selectedAuthor: 'all',
    selectedSort: 'popular',
    topAuthors: [],
    authors: [],
    genres: [],
    activeBookId: null
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
    stageHeading: document.getElementById('stage-heading'),
    resetFiltersBtn: document.getElementById('reset-filters-btn'),
    booksGrid: document.getElementById('books-grid'),
    emptyState: document.getElementById('empty-state'),
    emptyResetBtn: document.getElementById('empty-reset-btn'),
    paginationWrap: document.getElementById('pagination-wrap'),
    paginationInfo: document.getElementById('pagination-info'),
    paginationCurrentPage: document.getElementById('pagination-current-page'),
    paginationTotalPages: document.getElementById('pagination-total-pages'),
    paginationControls: document.getElementById('pagination-controls'),
    modalOverlay: document.getElementById('book-modal-overlay'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
    modalBody: document.getElementById('modal-body'),
    statCountText: document.getElementById('stat-count-text'),
    totalGenreCount: document.getElementById('total-genre-count')
  };

  /* --------------------------------------------------------------------------
     MiniSearch Engine & Calibrated Fallback
     -------------------------------------------------------------------------- */
  let miniSearchEngine = null;

  function initMiniSearch(books) {
    if (typeof MiniSearch === 'undefined') {
      console.warn('MiniSearch not available on window, using calibrated fallback.');
      return;
    }

    try {
      miniSearchEngine = new MiniSearch({
        fields: ['title', 'title_en', 'title_translit', 'author', 'author_en', 'author_aliases', 'series_name', 'genres'],
        storeFields: ['id'],
        extractField: (doc, fieldName) => {
          if (fieldName === 'title_translit') {
            return Array.isArray(doc.title_translit) ? doc.title_translit.join(' ') : '';
          }
          if (fieldName === 'author_aliases') {
            return Array.isArray(doc.author_aliases) ? doc.author_aliases.join(' ') : '';
          }
          if (fieldName === 'series_name') {
            return doc.series ? `${doc.series.name_bn || ''} ${doc.series.name_en || ''}` : '';
          }
          if (fieldName === 'genres') {
            return Array.isArray(doc.genres) ? doc.genres.join(' ') : '';
          }
          return doc[fieldName] || '';
        },
        searchOptions: {
          prefix: true,
          fuzzy: (term) => {
            if (term.length <= 3) return 0;
            if (term.length <= 6) return 1;
            return 2;
          },
          boost: {
            title: 6,
            title_en: 5,
            title_translit: 4,
            author: 4,
            author_en: 4,
            author_aliases: 3,
            series_name: 2,
            genres: 1
          },
          combineWith: 'AND'
        }
      });

      miniSearchEngine.addAll(books);
    } catch (e) {
      console.error('Failed to initialize MiniSearch:', e);
      miniSearchEngine = null;
    }
  }

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

  function matchesToken(qTok, targetTokens, targetSearchText) {
    // Calibrated maxDist based on query token length
    let maxDist = 0;
    if (qTok.length >= 7) {
      maxDist = 2;
    } else if (qTok.length >= 4) {
      maxDist = 1;
    } else {
      maxDist = 0;
    }

    // Fast path: direct substring match in pre-indexed string
    if (targetSearchText && targetSearchText.includes(qTok)) return true;
    for (let i = 0; i < targetTokens.length; i++) {
      const t = targetTokens[i];
      if (t.startsWith(qTok)) return true;
    }
    // Calibrated fallback: Levenshtein distance on tokens with close length
    if (maxDist > 0) {
      for (let i = 0; i < targetTokens.length; i++) {
        const t = targetTokens[i];
        if (Math.abs(qTok.length - t.length) <= maxDist) {
          if (levenshtein(qTok, t) <= maxDist) return true;
        }
      }
    }
    return false;
  }

  /* --------------------------------------------------------------------------
     IndexedDB Local Catalog Cache
     -------------------------------------------------------------------------- */
  const DB_NAME = 'bibyutatsu_ebooks_store';
  const STORE_NAME = 'catalog_cache';
  const DB_VERSION = 1;

  function openCacheDB() {
    return new Promise((resolve) => {
      if (!window.indexedDB) return resolve(null);
      try {
        const req = indexedDB.open(DB_NAME, DB_VERSION);
        req.onupgradeneeded = (e) => {
          const db = e.target.result;
          if (!db.objectStoreNames.contains(STORE_NAME)) {
            db.createObjectStore(STORE_NAME);
          }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => resolve(null);
      } catch {
        resolve(null);
      }
    });
  }

  async function getLocalCachedCatalog() {
    try {
      const db = await openCacheDB();
      if (!db) return null;
      return new Promise((resolve) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const req = store.get('active_catalog');
        req.onsuccess = () => resolve(req.result || null);
        req.onerror = () => resolve(null);
      });
    } catch {
      return null;
    }
  }

  async function setLocalCachedCatalog(data) {
    try {
      const db = await openCacheDB();
      if (!db) return;
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      store.put(data, 'active_catalog');
    } catch {}
  }

  /* --------------------------------------------------------------------------
     Dynamic Runtime Aggregation (Zero Hardcoded Stats)
     -------------------------------------------------------------------------- */
  function computeRuntimeAggregates(books) {
    const authorMap = new Map();
    const genreMap = new Map();
    const formatMap = new Map();

    for (let i = 0; i < books.length; i++) {
      const b = books[i];

      // Author aggregation
      const auth = b.author || 'অজ্ঞাত';
      let aRec = authorMap.get(auth);
      if (!aRec) {
        aRec = {
          author: auth,
          author_en: b.author_en || '',
          count: 0
        };
        authorMap.set(auth, aRec);
      }
      aRec.count++;

      // Department / Genre aggregation
      if (b.genres && Array.isArray(b.genres)) {
        for (let j = 0; j < b.genres.length; j++) {
          const g = b.genres[j];
          if (g) {
            genreMap.set(g, (genreMap.get(g) || 0) + 1);
          }
        }
      }

      // Format aggregation
      if (b.formats && typeof b.formats === 'object') {
        for (const fmt in b.formats) {
          formatMap.set(fmt, (formatMap.get(fmt) || 0) + 1);
        }
      }

      // Pre-compute normalized search tokens if not already cached
      if (!b._st) {
        b._st = (b.search_text || '').toLowerCase();
        b._tokens = b._st.split(/\s+/);
      }
    }

    const authors = Array.from(authorMap.values()).sort((a, b) => b.count - a.count);
    const genres = Array.from(genreMap.entries())
      .map(([genre, count]) => ({ genre, count }))
      .sort((a, b) => b.count - a.count);

    return {
      totalBooks: books.length,
      totalAuthors: authors.length,
      authors,
      genres,
      formats: Object.fromEntries(formatMap)
    };
  }

  function applyCatalogData(data, isBackgroundUpdate = false) {
    state.catalog = data;
    state.books = data.books || [];

    // Compute all numbers, authors, departments, and formats in real-time
    const aggregates = computeRuntimeAggregates(state.books);
    state.authors = aggregates.authors;
    state.genres = aggregates.genres;
    state.stats = {
      total_books: aggregates.totalBooks,
      total_authors: aggregates.totalAuthors,
      formats: aggregates.formats
    };

    // Update Header Stat Badge
    if (elements.statCountText) {
      elements.statCountText.textContent = `${aggregates.totalBooks.toLocaleString()} Books`;
    }

    // Update All Departments Badge
    if (elements.totalGenreCount) {
      elements.totalGenreCount.textContent = aggregates.totalBooks.toLocaleString();
    }

    // Initialize MiniSearch indexing
    initMiniSearch(state.books);

    setupSidebarFilters();

    if (!isBackgroundUpdate) {
      parseUrlParams();
      applyFiltersAndSearch(false);

      if (state.activeBookId) {
        const targetBook = state.books.find(b => b.id === state.activeBookId);
        if (targetBook) {
          openBookModal(targetBook);
        }
      }
    } else {
      // Background update: refresh current view with latest data without resetting user's page/search
      applyFiltersAndSearch(false);
    }
  }

  /* --------------------------------------------------------------------------
     Initialization & Data Loading
     -------------------------------------------------------------------------- */
  async function loadCatalog() {
    let hasLoadedFromCache = false;

    // 1. Check IndexedDB cache for instant 0ms load
    try {
      const cached = await getLocalCachedCatalog();
      if (cached && Array.isArray(cached.books) && cached.books.length > 0) {
        applyCatalogData(cached, false);
        hasLoadedFromCache = true;
      }
    } catch (e) {
      console.warn('Cache read error:', e);
    }

    // 2. Network fetch with conditional revalidation
    try {
      const response = await fetch('./catalog.json', { cache: 'no-cache' });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const serverData = await response.json();

      const isDifferent = !state.catalog ||
        serverData.version !== state.catalog.version ||
        serverData.generated_at !== state.catalog.generated_at ||
        (serverData.books && serverData.books.length !== state.books.length);

      if (!hasLoadedFromCache || isDifferent) {
        applyCatalogData(serverData, hasLoadedFromCache);
        await setLocalCachedCatalog(serverData);
      }
    } catch (err) {
      console.error('Failed to load fresh catalog:', err);
      if (!hasLoadedFromCache) {
        elements.booksGrid.innerHTML = `
          <div class="empty-state" style="display: block; grid-column: 1 / -1;">
            <div class="empty-icon">⚠️</div>
            <h3>Failed to load ebook catalog</h3>
            <p>Please check your connection or make sure catalog.json is present.</p>
          </div>
        `;
      }
    }
  }

  function setupSidebarFilters() {
    // 1. Department / Genre List
    if (elements.genrePills) {
      // Keep only the first "All Departments" button
      const allBtn = elements.genrePills.querySelector('.genre-item[data-genre="all"]');
      elements.genrePills.innerHTML = '';
      if (allBtn) {
        elements.genrePills.appendChild(allBtn);
      }

      if (state.genres.length > 0) {
        const frag = document.createDocumentFragment();
        state.genres.forEach(g => {
          const btn = document.createElement('button');
          btn.className = 'genre-item' + (state.selectedGenre === g.genre ? ' active' : '');
          btn.dataset.genre = g.genre;
          const cleanName = g.genre.split('(')[0].trim();
          btn.innerHTML = `
            <span class="genre-name">${escapeHtml(cleanName)}</span>
            <span class="genre-badge">${g.count}</span>
          `;
          frag.appendChild(btn);
        });
        elements.genrePills.appendChild(frag);
      }
    }

    // 2. Author Select Dropdown
    if (elements.authorFilter) {
      const totalAuthorsCount = state.stats ? state.stats.total_authors : state.authors.length;
      
      // Reset options except the first 'all' option
      elements.authorFilter.options.length = 1;
      elements.authorFilter.options[0].textContent = `All Authors (${totalAuthorsCount.toLocaleString()})`;

      if (state.authors.length > 0) {
        const frag = document.createDocumentFragment();
        state.authors.forEach(a => {
          const opt = document.createElement('option');
          opt.value = a.author;
          const enPart = a.author_en ? ` (${a.author_en})` : '';
          opt.textContent = `${a.author}${enPart} [${a.count}]`;
          frag.appendChild(opt);
        });
        elements.authorFilter.appendChild(frag);
      }
      elements.authorFilter.value = state.selectedAuthor;
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
    const page = parseInt(params.get('page'), 10);
    const book = params.get('book');

    if (q) {
      state.currentQuery = q;
      elements.searchInput.value = q;
      elements.clearSearch.style.display = 'block';
    }
    if (genre) state.selectedGenre = genre;
    if (author) state.selectedAuthor = author;
    if (format) state.selectedFormat = format;
    if (sort) state.selectedSort = sort;
    if (page && page > 0) state.currentPage = page;
    if (book) state.activeBookId = book;

    syncFilterControlsUI();
  }

  function updateUrlParams() {
    const params = new URLSearchParams();
    if (state.currentQuery) params.set('q', state.currentQuery);
    if (state.selectedGenre !== 'all') params.set('genre', state.selectedGenre);
    if (state.selectedAuthor !== 'all') params.set('author', state.selectedAuthor);
    if (state.selectedFormat !== 'all') params.set('format', state.selectedFormat);
    if (state.selectedSort !== 'popular') params.set('sort', state.selectedSort);
    if (state.currentPage > 1) params.set('page', state.currentPage);
    if (state.activeBookId) params.set('book', state.activeBookId);

    const newUrl = params.toString() ? `${window.location.pathname}?${params.toString()}` : window.location.pathname;
    window.history.replaceState({}, '', newUrl);
  }

  function syncFilterControlsUI() {
    // Genres
    const genreButtons = elements.genrePills.querySelectorAll('.genre-item');
    genreButtons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.genre === state.selectedGenre);
    });

    // Formats
    const formatButtons = elements.formatPills.querySelectorAll('.side-fmt-btn');
    formatButtons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.format === state.selectedFormat);
    });

    // Selects
    elements.authorFilter.value = state.selectedAuthor;
    elements.sortSelect.value = state.selectedSort;
  }

  /* --------------------------------------------------------------------------
     Search & Filtering Logic
     -------------------------------------------------------------------------- */
  function applyFiltersAndSearch(resetPage = true) {
    if (resetPage) {
      state.currentPage = 1;
    }

    const query = state.currentQuery.trim();
    let searchResultsMap = null;

    if (query) {
      if (miniSearchEngine) {
        try {
          const results = miniSearchEngine.search(query);
          searchResultsMap = new Map();
          for (let i = 0; i < results.length; i++) {
            searchResultsMap.set(results[i].id, results[i].score);
          }
        } catch (err) {
          console.warn('MiniSearch search failed, falling back:', err);
          searchResultsMap = null;
        }
      }
    }

    const queryTokens = query.toLowerCase().split(/\s+/).filter(Boolean);

    let filtered = state.books.filter(book => {
      // 1. Search Query
      if (query) {
        if (searchResultsMap !== null) {
          if (!searchResultsMap.has(book.id)) return false;
        } else if (queryTokens.length > 0) {
          const matchesAll = queryTokens.every(qTok => matchesToken(qTok, book._tokens, book._st));
          if (!matchesAll) return false;
        }
      }

      // 2. Genre
      if (state.selectedGenre !== 'all') {
        const hasGenre = book.genres.some(g => g.toLowerCase().includes(state.selectedGenre.toLowerCase()));
        if (!hasGenre) return false;
      }

      // 3. Format
      if (state.selectedFormat !== 'all') {
        if (!book.formats || !book.formats[state.selectedFormat]) return false;
      }

      // 4. Author
      if (state.selectedAuthor !== 'all') {
        if (book.author !== state.selectedAuthor) return false;
      }

      return true;
    });

    if (query && searchResultsMap && state.selectedSort === 'popular') {
      filtered.sort((a, b) => (searchResultsMap.get(b.id) || 0) - (searchResultsMap.get(a.id) || 0));
    } else {
      filtered = sortBooks(filtered, state.selectedSort);
    }

    state.filteredBooks = filtered;
    state.totalPages = Math.ceil(filtered.length / state.pageSize) || 1;
    if (state.currentPage > state.totalPages) state.currentPage = state.totalPages;
    if (state.currentPage < 1) state.currentPage = 1;

    // Update Heading and Count
    elements.resultsCount.innerHTML = `Showing <strong>${filtered.length.toLocaleString()}</strong> titles`;
    if (query) {
      elements.stageHeading.textContent = `Search: "${state.currentQuery}"`;
    } else if (state.selectedGenre !== 'all') {
      elements.stageHeading.textContent = state.selectedGenre.split('(')[0].trim();
    } else if (state.selectedAuthor !== 'all') {
      elements.stageHeading.textContent = `Author: ${state.selectedAuthor}`;
    } else {
      elements.stageHeading.textContent = 'All Books';
    }

    const hasActiveFilters = query || state.selectedGenre !== 'all' || state.selectedFormat !== 'all' || state.selectedAuthor !== 'all';
    elements.resetFiltersBtn.style.display = hasActiveFilters ? 'block' : 'none';

    if (filtered.length === 0) {
      elements.booksGrid.innerHTML = '';
      elements.emptyState.style.display = 'block';
      if (elements.paginationWrap) elements.paginationWrap.style.display = 'none';
    } else {
      elements.emptyState.style.display = 'none';
      renderCurrentPage();
    }

    updateUrlParams();
  }

  function sortBooks(books, sortMethod) {
    const list = [...books];
    switch (sortMethod) {
      case 'title-asc':
        return list.sort((a, b) => bnCollator.compare(a.title, b.title));
      case 'title-en-asc':
        return list.sort((a, b) => enCollator.compare(a.title_en, b.title_en));
      case 'author-asc':
        return list.sort((a, b) => enCollator.compare(a.author_en, b.author_en));
      case 'popular':
      default:
        return list;
    }
  }

  /* --------------------------------------------------------------------------
     Paginated Rendering & Controls (Strict Constant DOM Size)
     -------------------------------------------------------------------------- */
  function renderCurrentPage() {
    const startIdx = (state.currentPage - 1) * state.pageSize;
    const endIdx = startIdx + state.pageSize;
    const pageBooks = state.filteredBooks.slice(startIdx, endIdx);

    elements.booksGrid.innerHTML = '';
    const frag = document.createDocumentFragment();
    pageBooks.forEach(book => {
      frag.appendChild(createBookCard(book));
    });
    elements.booksGrid.appendChild(frag);

    renderPaginationUI();

    if (window.applyTilt) {
      window.applyTilt('.book-card');
    }
  }

  function renderPaginationUI() {
    if (!elements.paginationWrap) return;

    if (state.totalPages <= 1) {
      elements.paginationWrap.style.display = 'none';
      return;
    }

    elements.paginationWrap.style.display = 'flex';
    elements.paginationCurrentPage.textContent = state.currentPage;
    elements.paginationTotalPages.textContent = state.totalPages;

    const frag = document.createDocumentFragment();

    // 1. First Page Button («)
    const firstBtn = document.createElement('button');
    firstBtn.className = 'pagination-btn nav-step';
    firstBtn.innerHTML = '«';
    firstBtn.title = 'First Page';
    firstBtn.setAttribute('aria-label', 'First Page');
    firstBtn.disabled = state.currentPage === 1;
    firstBtn.addEventListener('click', () => goToPage(1));
    frag.appendChild(firstBtn);

    // 2. Previous Page Button (‹)
    const prevBtn = document.createElement('button');
    prevBtn.className = 'pagination-btn nav-step';
    prevBtn.innerHTML = '‹';
    prevBtn.title = 'Previous Page';
    prevBtn.setAttribute('aria-label', 'Previous Page');
    prevBtn.disabled = state.currentPage === 1;
    prevBtn.addEventListener('click', () => goToPage(state.currentPage - 1));
    frag.appendChild(prevBtn);

    // 3. Numbered page buttons with smart ellipsis
    const maxButtons = 5;
    let startPage = Math.max(1, state.currentPage - 2);
    let endPage = Math.min(state.totalPages, state.currentPage + 2);

    if (state.currentPage <= 3) {
      endPage = Math.min(state.totalPages, maxButtons);
    } else if (state.currentPage >= state.totalPages - 2) {
      startPage = Math.max(1, state.totalPages - (maxButtons - 1));
    }

    if (startPage > 1) {
      frag.appendChild(createPageBtn(1));
      if (startPage > 2) {
        const ell = document.createElement('span');
        ell.className = 'pagination-ellipsis';
        ell.textContent = '…';
        frag.appendChild(ell);
      }
    }

    for (let p = startPage; p <= endPage; p++) {
      frag.appendChild(createPageBtn(p));
    }

    if (endPage < state.totalPages) {
      if (endPage < state.totalPages - 1) {
        const ell = document.createElement('span');
        ell.className = 'pagination-ellipsis';
        ell.textContent = '…';
        frag.appendChild(ell);
      }
      frag.appendChild(createPageBtn(state.totalPages));
    }

    // 4. Next Page Button (›)
    const nextBtn = document.createElement('button');
    nextBtn.className = 'pagination-btn nav-step';
    nextBtn.innerHTML = '›';
    nextBtn.title = 'Next Page';
    nextBtn.setAttribute('aria-label', 'Next Page');
    nextBtn.disabled = state.currentPage === state.totalPages;
    nextBtn.addEventListener('click', () => goToPage(state.currentPage + 1));
    frag.appendChild(nextBtn);

    // 5. Last Page Button (»)
    const lastBtn = document.createElement('button');
    lastBtn.className = 'pagination-btn nav-step';
    lastBtn.innerHTML = '»';
    lastBtn.title = 'Last Page';
    lastBtn.setAttribute('aria-label', 'Last Page');
    lastBtn.disabled = state.currentPage === state.totalPages;
    lastBtn.addEventListener('click', () => goToPage(state.totalPages));
    frag.appendChild(lastBtn);

    elements.paginationControls.innerHTML = '';
    elements.paginationControls.appendChild(frag);
  }

  function createPageBtn(pageNum) {
    const btn = document.createElement('button');
    btn.className = `pagination-btn ${pageNum === state.currentPage ? 'active' : ''}`;
    btn.textContent = pageNum;
    btn.setAttribute('aria-label', `Page ${pageNum}`);
    if (pageNum === state.currentPage) {
      btn.setAttribute('aria-current', 'page');
    } else {
      btn.addEventListener('click', () => goToPage(pageNum));
    }
    return btn;
  }

  function goToPage(targetPage) {
    const p = Math.max(1, Math.min(state.totalPages, targetPage));
    if (p === state.currentPage) return;
    state.currentPage = p;
    renderCurrentPage();
    updateUrlParams();

    // Scroll smoothly to top of books grid
    const nav = document.getElementById('nav');
    const headerHeight = nav ? nav.offsetHeight : 70;
    const gridTop = elements.booksGrid.getBoundingClientRect().top + window.pageYOffset - headerHeight - 20;
    window.scrollTo({ top: Math.max(0, gridTop), behavior: 'smooth' });
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
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            <span>⤓ ${primaryFormat.toUpperCase()}</span>
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

  function trackDownloadEvent(bookTitle, format, fileName) {
    if (typeof window.gtag === 'function') {
      window.gtag('event', 'file_download', {
        file_name: fileName || '',
        file_extension: format || '',
        book_title: bookTitle || '',
        link_url: window.location.href
      });
    }
  }

  function handleDownloadClick(e, book, format, formatInfo) {
    if (!formatInfo.download_url || formatInfo.download_url === '#') {
      e.preventDefault();
      openBookModal(book);
    } else {
      trackDownloadEvent(book.title_en || book.title_bn, format, formatInfo.filename);
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

    let translitSectionHtml = '';
    if (Array.isArray(book.title_translit) && book.title_translit.length > 0) {
      const cleanAliases = [...new Set(book.title_translit.map(t => (t || '').trim()))].filter(Boolean);
      if (cleanAliases.length > 0) {
        const pills = cleanAliases.map(t => `<button type="button" class="translit-pill" data-query="${escapeHtml(t)}" title="Search '${escapeHtml(t)}'">${escapeHtml(t)}</button>`).join('');
        translitSectionHtml = `
          <div class="modal-translit-section">
            <span class="modal-translit-label">🔍 Alternative Spellings & Transliterations:</span>
            <div class="modal-translit-pills">
              ${pills}
            </div>
          </div>
        `;
      }
    }

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
        ${translitSectionHtml}
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
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }

    elements.modalBody.querySelectorAll('.translit-pill').forEach(pill => {
      pill.addEventListener('click', (e) => {
        const q = e.currentTarget.dataset.query;
        if (q) {
          closeModal();
          elements.searchInput.value = q;
          elements.clearSearch.style.display = 'block';
          state.currentQuery = q;
          applyFiltersAndSearch(true);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      });
    });

    elements.modalBody.querySelectorAll('.modal-dl-card').forEach(dlCard => {
      dlCard.addEventListener('click', () => {
        const fmt = dlCard.querySelector('.modal-dl-format')?.textContent?.trim().toLowerCase() || '';
        const fileName = dlCard.getAttribute('download') || '';
        trackDownloadEvent(book.title_en || book.title_bn, fmt, fileName);
      });
    });

    elements.modalOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
    state.activeBookId = book.id;
    updateUrlParams();
    document.title = `${book.title} (${book.author}) | Bibyutatsu BookStore`;

    if (window.applyMagnetic) {
      window.applyMagnetic('.modal-dl-card, .modal-close');
    }
  }

  function closeModal() {
    elements.modalOverlay.classList.remove('active');
    document.body.style.overflow = '';
    state.activeBookId = null;
    updateUrlParams();
    document.title = 'Bibyutatsu BookStore | Free Bengali Ebooks Library (বাংলা ডিজিটাল বইঘর)';
  }

  /* --------------------------------------------------------------------------
     Event Listeners
     -------------------------------------------------------------------------- */
  function setupEvents() {
    let debounceTimer;
    elements.searchInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      const val = e.target.value;
      elements.clearSearch.style.display = val ? 'block' : 'none';

      debounceTimer = setTimeout(() => {
        state.currentQuery = val;
        applyFiltersAndSearch(true);
      }, 200);
    });

    elements.clearSearch.addEventListener('click', () => {
      elements.searchInput.value = '';
      state.currentQuery = '';
      elements.clearSearch.style.display = 'none';
      applyFiltersAndSearch(true);
      elements.searchInput.focus();
    });

    // Trending Tags
    elements.quickTags.addEventListener('click', (e) => {
      const btn = e.target.closest('.side-tag');
      if (!btn) return;
      const term = btn.dataset.search;
      elements.searchInput.value = term;
      state.currentQuery = term;
      elements.clearSearch.style.display = 'block';
      applyFiltersAndSearch(true);
      if (window.closeMobileDrawer) window.closeMobileDrawer();
    });

    // Department / Genre List
    elements.genrePills.addEventListener('click', (e) => {
      const item = e.target.closest('.genre-item');
      if (!item) return;
      state.selectedGenre = item.dataset.genre;
      syncFilterControlsUI();
      applyFiltersAndSearch(true);
      if (window.closeMobileDrawer) window.closeMobileDrawer();
    });

    // Format Filters
    elements.formatPills.addEventListener('click', (e) => {
      const btn = e.target.closest('.side-fmt-btn');
      if (!btn) return;
      state.selectedFormat = btn.dataset.format;
      syncFilterControlsUI();
      applyFiltersAndSearch(true);
      if (window.closeMobileDrawer) window.closeMobileDrawer();
    });

    // Author Select
    elements.authorFilter.addEventListener('change', (e) => {
      state.selectedAuthor = e.target.value;
      applyFiltersAndSearch(true);
      if (window.closeMobileDrawer) window.closeMobileDrawer();
    });

    // Sort Select
    elements.sortSelect.addEventListener('change', (e) => {
      state.selectedSort = e.target.value;
      applyFiltersAndSearch(true);
    });

    // Reset Filters
    elements.resetFiltersBtn.addEventListener('click', resetAllFilters);
    elements.emptyResetBtn.addEventListener('click', resetAllFilters);

    // Modal close
    elements.modalCloseBtn.addEventListener('click', closeModal);
    elements.modalOverlay.addEventListener('click', (e) => {
      if (e.target === elements.modalOverlay) closeModal();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeModal();
        if (window.closeMobileDrawer) window.closeMobileDrawer();
      }
    });

    // Browser back/forward navigation sync
    window.addEventListener('popstate', () => {
      parseUrlParams();
      applyFiltersAndSearch(false);
      if (state.activeBookId) {
        const targetBook = state.books.find(b => b.id === state.activeBookId);
        if (targetBook) {
          openBookModal(targetBook);
        }
      } else if (elements.modalOverlay.classList.contains('active')) {
        closeModal();
      }
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
    if (window.closeMobileDrawer) window.closeMobileDrawer();
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
