(function () {
  var root = document.documentElement;
  root.classList.add('js');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');

  document.querySelectorAll('[data-year]').forEach(function (s) { s.textContent = new Date().getFullYear(); });

  // Montréal time (weekday 0 = Monday)
  function montrealNow() {
    try {
      var parts = new Intl.DateTimeFormat('en-US', { timeZone: 'America/Toronto', weekday: 'short', hour: 'numeric', minute: 'numeric', hour12: false }).formatToParts(new Date());
      var o = {}; parts.forEach(function (p) { o[p.type] = p.value; });
      var day = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].indexOf(o.weekday);
      return { day: day, h: (parseInt(o.hour, 10) % 24) + parseInt(o.minute, 10) / 60 };
    } catch (e) { return null; }
  }
  var now = montrealNow();
  if (now) {
    document.querySelectorAll('.hours-table tr[data-day="' + now.day + '"]').forEach(function (tr) { tr.classList.add('is-today'); });
    document.querySelectorAll('[data-open-status]').forEach(function (el) {
      try {
        var d = JSON.parse(el.getAttribute('data-open-status'));
        var fmt = function (h) {
          if (d.lang === 'fr') return h + ' h';
          return (h > 12 ? h - 12 : h) + ' ' + (h < 12 ? 'a.m.' : 'p.m.');
        };
        var today = d.h[now.day];
        if (now.h >= today[0] && now.h < today[1]) {
          el.textContent = d.open.replace('{c}', fmt(today[1])); el.classList.add('is-open');
        } else {
          var next = now.h < today[0] ? now.day : (now.day + 1) % 7;
          var when = next === now.day ? d.today : (next === (now.day + 1) % 7 ? d.tomorrow : d.days[next]);
          el.textContent = d.closed.replace('{d}', when).replace('{o}', fmt(d.h[next][0])); el.classList.add('is-closed');
        }
      } catch (e) {}
    });
  }

  // Google map: loads only after the visitor asks (no Google request before that)
  document.querySelectorAll('[data-map-src]').forEach(function (b) {
    b.addEventListener('click', function () {
      var box = b.closest('.map');
      var f = document.createElement('iframe');
      f.src = b.getAttribute('data-map-src');
      f.title = b.getAttribute('data-map-title') || 'Google Maps';
      f.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
      f.setAttribute('allowfullscreen', '');
      f.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox');
      box.appendChild(f); box.classList.add('is-loaded'); f.focus();
    });
  });

  // Mobile nav
  var menuBtn = document.getElementById('menu-toggle');
  var mnav = document.getElementById('mobile-nav');
  function setMenu(open) {
    if (!menuBtn) return;
    menuBtn.setAttribute('aria-expanded', String(open));
    mnav.classList.toggle('is-open', open);
    menuBtn.setAttribute('aria-label', open ? menuBtn.dataset.closeLabel : menuBtn.dataset.openLabel);
    if (open) { var a = mnav.querySelector('a'); if (a) a.focus({ preventScroll: true }); }
  }
  if (menuBtn) {
    menuBtn.addEventListener('click', function () { setMenu(menuBtn.getAttribute('aria-expanded') !== 'true'); });
    mnav.addEventListener('click', function (e) { if (e.target.closest('a')) setMenu(false); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menuBtn.getAttribute('aria-expanded') === 'true') { setMenu(false); menuBtn.focus(); }
    });
    var wide = window.matchMedia('(min-width: 961px)');
    var onWide = function (m) { if (m.matches) setMenu(false); };
    wide.addEventListener ? wide.addEventListener('change', onWide) : wide.addListener(onWide);
  }

  // Header border once scrolled
  var header = document.querySelector('.header');
  var scrolled = null, hTick = false;
  var onScrollHeader = function () {
    if (hTick) return; hTick = true;
    requestAnimationFrame(function () { hTick = false; var s = window.scrollY > 8; if (s !== scrolled && header) { scrolled = s; header.classList.toggle('is-scrolled', s); } });
  };
  onScrollHeader(); window.addEventListener('scroll', onScrollHeader, { passive: true });

  // Reveal on scroll (content stays readable before it settles)
  var reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reduce.matches) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('is-in'); io.unobserve(en.target); } });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    reveals.forEach(function (el) { io.observe(el); });
  } else reveals.forEach(function (el) { el.classList.add('is-in'); });

  // Instant next page: once this page has fully loaded, let the browser prepare
  // the other-language page (and any link you touch) in the background.
  var specOK = window.HTMLScriptElement && HTMLScriptElement.supports && HTMLScriptElement.supports('speculationrules');
  var warmed = {};
  function warm(a) {
    if (!a || a.target === '_blank' || a.origin !== location.origin || warmed[a.pathname]) return;
    warmed[a.pathname] = 1;
    try { fetch(a.href, { credentials: 'same-origin' }).catch(function () {}); } catch (err) {}
  }
  function afterLoad(fn) {
    var go = function () { ('requestIdleCallback' in window) ? requestIdleCallback(fn, { timeout: 2000 }) : setTimeout(fn, 600); };
    if (document.readyState === 'complete') go(); else window.addEventListener('load', go, { once: true });
  }
  afterLoad(function () {
    if (specOK) {
      var s = document.createElement('script');
      s.type = 'speculationrules';
      s.textContent = JSON.stringify({ prerender: [
        { where: { selector_matches: '.langs a' }, eagerness: 'eager' },
        { where: { and: [{ href_matches: '/*' }, { not: { selector_matches: '[target=_blank]' } }] }, eagerness: 'moderate' }
      ] });
      document.head.appendChild(s);
    } else {
      warm(document.querySelector('.langs a[href]'));
    }
  });
  if (!specOK) {
    var onIntent = function (e) { warm(e.target.closest && e.target.closest('a[href]')); };
    document.addEventListener('touchstart', onIntent, { passive: true });
    document.addEventListener('pointerover', onIntent, { passive: true });
  }

  // Mobile sticky "Commander": after the page's main buttons scroll away; hidden over the map and the final order section
  var bar = document.getElementById('order-bar');
  if (bar && 'IntersectionObserver' in window) {
    var barLink = bar.querySelector('a');
    var heroGone = false, blocked = [];
    var update = function () {
      var show = heroGone && blocked.length === 0;
      bar.classList.toggle('is-shown', show);
      bar.setAttribute('aria-hidden', String(!show));
      barLink.tabIndex = show ? 0 : -1;
    };
    var anchor = document.getElementById('hero-ctas');
    if (anchor) new IntersectionObserver(function (es) { var e = es[0]; heroGone = !e.isIntersecting && e.boundingClientRect.top < 0; update(); }).observe(anchor);
    else { heroGone = true; update(); }
    var bo = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        var i = blocked.indexOf(e.target);
        if (e.isIntersecting && i < 0) blocked.push(e.target);
        if (!e.isIntersecting && i >= 0) blocked.splice(i, 1);
      });
      update();
    });
    ['map', 'commander'].forEach(function (id) { var el = document.getElementById(id); if (el) bo.observe(el); });
  }
})();
