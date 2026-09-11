/**
 * Bibyutatsu Ebooks - Client Application
 * Features:
 * - Ultra-fast dual-script transliteration & fuzzy search
 * - Multi-format download management (EPUB, KFX, PDF, MOBI)
 * - Infinite scroll / batch rendering
 * - URL state synchronization & theme persistence
 */

(function () {
  'use strict';

  // Application State
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

  // DOM Elements
  const elements = {
    themeToggle: document.getElementById('theme-toggle'),
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
     Theme Management
     -------------------------------------------------------------------------- */
  function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = savedTheme || (prefersDark ? 'dark' : 'light');
    setTheme(theme);

    elements.themeToggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      setTheme(next);
    });
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }

  /* --------------------------------------------------------------------------
     Fuzzy Search Engine & String Distance
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
     Data Fetching & Initialization
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

      // Update badge
      if (elements.statCountText && data.stats) {
        elements.statCountText.textContent = `${data.stats.total_books.toLocaleString()} Books`;
      }

      setupFiltersUI();
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

  /* --------------------------------------------------------------------------
     Setup Filter Controls
     -------------------------------------------------------------------------- */
  function setupFiltersUI() {
    // 1. Genre Pills
    if (state.genres.length > 0) {
      const frag = document.createDocumentFragment();
      state.genres.slice(0, 10).forEach(g => {
        const btn = document.createElement('button');
        btn.className = 'pill';
        btn.dataset.genre = g.genre;
        // Strip parenthetical English for clean pill text
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
    // Genre pills active class
    const genreButtons = elements.genrePills.querySelectorAll('.pill');
    genreButtons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.genre === state.selectedGenre);
    });

    // Format buttons active class
    const formatButtons = elements.formatPills.querySelectorAll('.format-btn');
    formatButtons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.format === state.selectedFormat);
    });

    // Selects
    elements.authorFilter.value = state.selectedAuthor;
    elements.sortSelect.value = state.selectedSort;
  }

  /* --------------------------------------------------------------------------
     Filter, Search, and Sort Logic
     -------------------------------------------------------------------------- */
  function applyFiltersAndSearch() {
    const query = state.currentQuery.trim().toLowerCase();
    const queryTokens = query.split(/\s+/).filter(Boolean);

    let filtered = state.books.filter(book => {
      // 1. Search Query Match
      if (queryTokens.length > 0) {
        const searchTokens = (book.search_text || '').toLowerCase().split(/\s+/);
        const matchesAll = queryTokens.every(qTok => matchesToken(qTok, searchTokens, 2));
        if (!matchesAll) return false;
      }

      // 2. Genre Filter
      if (state.selectedGenre !== 'all') {
        const hasGenre = book.genres.some(g => g.toLowerCase().includes(state.selectedGenre.toLowerCase()));
        if (!hasGenre) return false;
      }

      // 3. Format Filter
      if (state.selectedFormat !== 'all') {
        if (!book.formats || !book.formats[state.selectedFormat]) return false;
      }

      // 4. Author Filter
      if (state.selectedAuthor !== 'all') {
        if (book.author !== state.selectedAuthor) return false;
      }

      return true;
    });

    // Sort
    filtered = sortBooks(filtered, state.selectedSort);

    state.filteredBooks = filtered;
    state.renderedCount = 0;
    elements.booksGrid.innerHTML = '';

    // Update Result Counts
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
        // Already naturally ordered by top authors in catalog
        return list;
    }
  }

  /* --------------------------------------------------------------------------
     Batch Rendering
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

    // Show/hide load more button
    if (state.renderedCount < state.filteredBooks.length) {
      elements.loadMoreContainer.style.display = 'flex';
    } else {
      elements.loadMoreContainer.style.display = 'none';
    }
  }

  /* --------------------------------------------------------------------------
     Book Card Creation
     -------------------------------------------------------------------------- */
  function createBookCard(book) {
    const card = document.createElement('article');
    card.className = 'book-card';
    card.dataset.id = book.id;

    // Badges
    const seriesHtml = book.series ? `<span class="series-tag">${escapeHtml(book.series.name_bn)}</span>` : '<span></span>';
    
    // Format chips
    let formatBadgesHtml = '';
    const fmts = Object.keys(book.formats || {});
    fmts.forEach(f => {
      formatBadgesHtml += `<span class="badge-fmt ${f}">${f.toUpperCase()}</span>`;
    });

    // Primary download button link
    const primaryFormat = book.formats.epub ? 'epub' : (book.formats.kfx ? 'kfx' : fmts[0]);
    const primaryInfo = book.formats[primaryFormat] || {};
    const downloadHref = primaryInfo.download_url || '#';
    const downloadFilename = primaryInfo.filename || `${book.id}.${primaryFormat}`;

    // Cover image or fallback
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
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            <span>${primaryFormat.toUpperCase()}</span>
          </a>
          <button class="details-btn" aria-label="Book Details">Details</button>
        </div>
      </div>
    `;

    // Card click opens modal (unless download button was clicked)
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
      // If direct release URL is not yet connected, trigger modal or fallback alert
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
          <span class="modal-dl-btn">Download ${fmtKey.toUpperCase()}</span>
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
          <h4>Available Download Formats</h4>
          <div class="modal-download-grid">
            ${downloadCardsHtml}
          </div>
        </div>
      </div>
    `;

    // Clicking author in modal filters by author
    const authorLink = elements.modalBody.querySelector('.modal-author-link');
    if (authorLink) {
      authorLink.addEventListener('click', () => {
        closeModal();
        state.selectedAuthor = book.author;
        syncFilterControlsUI();
        applyFiltersAndSearch();
        window.scrollTo({ top: 400, behavior: 'smooth' });
      });
    }

    elements.modalOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    elements.modalOverlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  /* --------------------------------------------------------------------------
     Event Listeners
     -------------------------------------------------------------------------- */
  function setupEvents() {
    // 1. Search Input
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

    // 2. Quick Tags
    elements.quickTags.addEventListener('click', (e) => {
      const btn = e.target.closest('.tag-btn');
      if (!btn) return;
      const term = btn.dataset.search;
      elements.searchInput.value = term;
      state.currentQuery = term;
      elements.clearSearch.style.display = 'flex';
      applyFiltersAndSearch();
      elements.searchInput.focus();
    });

    // 3. Genre Pills
    elements.genrePills.addEventListener('click', (e) => {
      const pill = e.target.closest('.pill');
      if (!pill) return;
      state.selectedGenre = pill.dataset.genre;
      syncFilterControlsUI();
      applyFiltersAndSearch();
    });

    // 4. Format Filter Buttons
    elements.formatPills.addEventListener('click', (e) => {
      const btn = e.target.closest('.format-btn');
      if (!btn) return;
      state.selectedFormat = btn.dataset.format;
      syncFilterControlsUI();
      applyFiltersAndSearch();
    });

    // 5. Author Select Dropdown
    elements.authorFilter.addEventListener('change', (e) => {
      state.selectedAuthor = e.target.value;
      applyFiltersAndSearch();
    });

    // 6. Sort Select Dropdown
    elements.sortSelect.addEventListener('change', (e) => {
      state.selectedSort = e.target.value;
      applyFiltersAndSearch();
    });

    // 7. Reset Filters Buttons
    elements.resetFiltersBtn.addEventListener('click', resetAllFilters);
    elements.emptyResetBtn.addEventListener('click', resetAllFilters);

    // 8. Load More
    elements.loadMoreBtn.addEventListener('click', () => {
      renderNextBatch();
    });

    // 9. Infinite Scroll (IntersectionObserver)
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && state.renderedCount < state.filteredBooks.length) {
          renderNextBatch();
        }
      }, { rootMargin: '400px' });
      observer.observe(elements.loadMoreContainer);
    }

    // 10. Modal Close
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
  initTheme();
  setupEvents();
  loadCatalog();

})();
