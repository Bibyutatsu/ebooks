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
    if (typeof window.updateThreeColors === 'function') {
      window.updateThreeColors(nextTheme);
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
      const btn = e.target.closest('.download-btn, .nav-btn, .theme-subpage-btn, .read-check-btn, .back-to-top-btn, .letter-pill');
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
     3. THREE.JS AMBIENT PARTICLE & SHADER GRADIENT CANVAS
     -------------------------------------------------------------------------- */
  function initThreeHero() {
    const canvas = document.getElementById('hero-canvas');
    if (!canvas || typeof THREE === 'undefined') return;

    // Detect root_rel for particle textures
    const cssLink = document.querySelector('link[rel="stylesheet"][href*="pages.css"]');
    const rootRel = cssLink ? cssLink.getAttribute('href').replace(/assets\/pages\.css.*$/, '') : '../';

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1200);
    camera.position.z = 320;

    const N = window.innerWidth < 700 ? 35 : 60;
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
      m.userData.vx = (Math.random() - 0.5) * 0.14;
      m.userData.vy = (Math.random() - 0.5) * 0.12;
      scene.add(m);
      nodes.push(m);
    }

    const MAX = 180;
    const lPos = new Float32Array(MAX * 6), lCol = new Float32Array(MAX * 6);
    const lGeo = new THREE.BufferGeometry();
    lGeo.setAttribute('position', new THREE.BufferAttribute(lPos, 3));
    lGeo.setAttribute('color', new THREE.BufferAttribute(lCol, 3));
    const lMat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.14 });
    const lines = new THREE.LineSegments(lGeo, lMat);
    scene.add(lines);

    const loader = new THREE.TextureLoader();
    const pGeo = new THREE.BufferGeometry();
    const pCount = 100;
    const pPos = new Float32Array(pCount * 3);
    for (let i = 0; i < pCount * 3; i++) pPos[i] = (Math.random() - 0.5) * 900;
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
    const pMat = new THREE.PointsMaterial({
      size: 0.5,
      color: 0xffffff,
      transparent: true,
      opacity: 0.55,
      alphaTest: 0.5,
      depthWrite: false
    });
    loader.load(`${rootRel}assets/particles/bokeh.png`, tex => {
      pMat.map = tex;
      pMat.needsUpdate = true;
    }, undefined, () => {});
    const particles = new THREE.Points(pGeo, pMat);
    scene.add(particles);

    /* -- ShaderGradient Plane (Fluid wavy grain gradient) -- */
    const gradVertexShader = `
      varying vec2 vUv;
      varying float vElevation;
      uniform float uTime;
      void main() {
        vUv = uv;
        vec3 pos = position;
        float w1 = sin(pos.x * 0.006 + uTime * 0.35) * cos(pos.y * 0.006 + uTime * 0.28) * 35.0;
        float w2 = sin((pos.x + pos.y) * 0.004 + uTime * 0.45) * 20.0;
        pos.z += w1 + w2;
        vElevation = (w1 + w2) / 55.0;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
      }
    `;

    const gradFragmentShader = `
      varying vec2 vUv;
      varying float vElevation;
      uniform float uTime;
      uniform vec3 uColor1;
      uniform vec3 uColor2;
      uniform vec3 uColor3;
      uniform vec3 uColor4;
      uniform float uOpacity;

      float grain(vec2 uv, float t) {
        return fract(sin(dot(uv + fract(t * 0.04), vec2(12.9898, 78.233))) * 43758.5453) - 0.5;
      }

      void main() {
        vec2 p = vUv;
        float f1 = sin(p.x * 3.14159 + uTime * 0.25) * 0.5 + 0.5;
        float f2 = cos(p.y * 3.14159 + uTime * 0.2 + vElevation * 0.8) * 0.5 + 0.5;
        float f3 = sin((p.x + p.y + vElevation) * 2.0 + uTime * 0.3) * 0.5 + 0.5;

        vec3 colA = mix(uColor1, uColor2, f1);
        vec3 colB = mix(uColor3, uColor4, f2);
        vec3 finalCol = mix(colA, colB, f3);

        float g = grain(gl_FragCoord.xy, uTime) * 0.055;
        finalCol += vec3(g);

        gl_FragColor = vec4(finalCol, uOpacity);
      }
    `;

    const THEME_GRADIENTS = {
      dark:      { c1: 0x050518, c2: 0x160830, c3: 0x01172e, c4: 0x1f0a3d, op: 0.55 },
      light:     { c1: 0xeeeef8, c2: 0xd8e4fc, c3: 0xebe0f8, c4: 0xfcfcff, op: 0.65 },
      batman:    { c1: 0x000000, c2: 0x1f1c00, c3: 0x120000, c4: 0x2e2700, op: 0.70 },
      cyberpunk: { c1: 0x200018, c2: 0x00201e, c3: 0x320038, c4: 0x00332e, op: 0.62 },
      ocean:     { c1: 0x010c16, c2: 0x002024, c3: 0x01162a, c4: 0x00322b, op: 0.60 },
    };

    const targetGrad = {
      c1: new THREE.Color(THEME_GRADIENTS.dark.c1),
      c2: new THREE.Color(THEME_GRADIENTS.dark.c2),
      c3: new THREE.Color(THEME_GRADIENTS.dark.c3),
      c4: new THREE.Color(THEME_GRADIENTS.dark.c4),
      op: THEME_GRADIENTS.dark.op
    };

    const gradUniforms = {
      uTime: { value: 0 },
      uColor1: { value: new THREE.Color(THEME_GRADIENTS.dark.c1) },
      uColor2: { value: new THREE.Color(THEME_GRADIENTS.dark.c2) },
      uColor3: { value: new THREE.Color(THEME_GRADIENTS.dark.c3) },
      uColor4: { value: new THREE.Color(THEME_GRADIENTS.dark.c4) },
      uOpacity: { value: THEME_GRADIENTS.dark.op }
    };

    const gradMat = new THREE.ShaderMaterial({
      vertexShader: gradVertexShader,
      fragmentShader: gradFragmentShader,
      uniforms: gradUniforms,
      transparent: true,
      depthWrite: false
    });

    const gradGeo = new THREE.PlaneGeometry(1800, 1300, 40, 40);
    const gradMesh = new THREE.Mesh(gradGeo, gradMat);
    gradMesh.position.set(0, 0, -220);
    scene.add(gradMesh);

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
        loader.load(`${rootRel}assets/particles/${c.ptex}.png`, tex => {
          pMat.map = tex;
          pMat.needsUpdate = true;
        }, undefined, () => {});
      }
      const tg = THEME_GRADIENTS[theme] || THEME_GRADIENTS.dark;
      targetGrad.c1.setHex(tg.c1);
      targetGrad.c2.setHex(tg.c2);
      targetGrad.c3.setHex(tg.c3);
      targetGrad.c4.setHex(tg.c4);
      targetGrad.op = tg.op;
    };

    const curTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    window.updateThreeColors(curTheme);

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
      my = -(e.clientY / window.innerHeight - 0.5) * 2;
    }, { passive: true });

    let clock = new THREE.Clock();
    function animate() {
      requestAnimationFrame(animate);
      const dt = clock.getDelta();
      const elapsed = clock.getElapsedTime();

      gradUniforms.uTime.value = elapsed;
      gradUniforms.uColor1.value.lerp(targetGrad.c1, dt * 2.5);
      gradUniforms.uColor2.value.lerp(targetGrad.c2, dt * 2.5);
      gradUniforms.uColor3.value.lerp(targetGrad.c3, dt * 2.5);
      gradUniforms.uColor4.value.lerp(targetGrad.c4, dt * 2.5);
      gradUniforms.uOpacity.value += (targetGrad.op - gradUniforms.uOpacity.value) * dt * 2.5;

      tx += (mx * 18 - tx) * 0.04;
      ty += (my * 14 - ty) * 0.04;
      camera.position.x = tx;
      camera.position.y = ty;
      camera.lookAt(scene.position);

      nodes.forEach(n => {
        n.position.x += n.userData.vx;
        n.position.y += n.userData.vy;
        if (Math.abs(n.position.x) > 350) n.userData.vx *= -1;
        if (Math.abs(n.position.y) > 230) n.userData.vy *= -1;
      });

      updateLines();
      particles.rotation.y = elapsed * 0.015;
      particles.rotation.x = elapsed * 0.008;

      renderer.render(scene, camera);
    }
    animate();

    window.addEventListener('resize', () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }, { passive: true });
  }

  /* --------------------------------------------------------------------------
     4. POKÉMON CARDS CSS: 3D TILT & HOLOGRAPHIC FOIL
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

  /* --------------------------------------------------------------------------
     7. FLOATING BACK-TO-TOP BUTTON
     -------------------------------------------------------------------------- */
  function initBackToTop() {
    const bttBtn = document.getElementById('back-to-top-btn');
    if (!bttBtn) return;

    window.addEventListener('scroll', () => {
      if (window.scrollY > 350) {
        bttBtn.classList.add('visible');
      } else {
        bttBtn.classList.remove('visible');
      }
    }, { passive: true });

    bttBtn.addEventListener('click', (e) => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      if (typeof window.triggerCanvasUIButtonShatter === 'function') {
        window.triggerCanvasUIButtonShatter(e.clientX, e.clientY);
      }
    });
  }

  // DOM Ready Initializer
  function initAll() {
    initThreeHero();
    initHoloCards();
    balanceHeadings();
    initSeriesProgress();
    initAuthorSearch();
    initBackToTop();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
