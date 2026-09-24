/*!
 * Thinkube Auth — "Signal Terrain" login background (light variant)
 * Framework-free, no dependencies. Canvas 2D.
 *
 * Usage:
 *   <canvas data-tk-terrain></canvas>          // auto-mounts on DOMContentLoaded
 *   // or
 *   const h = ThinkubeTerrain.mount(canvasEl, { accent: '#0f766e' });
 *   h.destroy();
 *
 * Options (also readable from data attributes: data-accent, data-warm,
 * data-background, data-density, data-speed):
 *   accent      wireframe + dot colour           default '#0f766e'
 *   warm        wave-crest highlight colour      default '#ea580c'
 *   background  fill colour                      default '#ffffff'
 *   density     grid density multiplier          default 1   (0.6–1.5)
 *   speed       animation speed multiplier       default 1   (0.2–2.5)
 *
 * Behaviour: slow multi-sine wave surface in perspective; an auto ripple every
 * ~4.5 s; click on the background starts a ripple at that point; the view
 * shifts slightly with the pointer. Honours prefers-reduced-motion (renders a
 * static frame). Scene is authored in a 1440x900 logical space and scaled to
 * cover the canvas.
 */
(function (global) {
  'use strict';

  var LW = 1440, LH = 900;

  function rgba(hex, a) {
    var h = (hex || '#000000').replace('#', '');
    if (h.length === 3) h = h.split('').map(function (c) { return c + c; }).join('');
    var n = parseInt(h, 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
  }

  function mount(canvas, opts) {
    opts = opts || {};
    var ds = canvas.dataset || {};
    var cfg = {
      accent: opts.accent || ds.accent || '#0f766e',
      warm: opts.warm || ds.warm || '#ea580c',
      background: opts.background || ds.background || '#ffffff',
      density: +(opts.density || ds.density || 1),
      speed: +(opts.speed || ds.speed || 1)
    };
    var ctx = canvas.getContext('2d');
    var reduce = !!(global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches);

    var cols = Math.max(20, Math.round(56 * cfg.density));
    var rows = Math.max(12, Math.round(30 * cfg.density));
    var pts = new Array(cols * rows);
    for (var i = 0; i < pts.length; i++) pts[i] = { X: 0, Z: 0, Y: 0, x: 0, y: 0 };

    var ripples = [], nextRipple = 800, t = 0, last = 0, px = 0, raf = 0, dead = false;
    var mouse = { x: 0, y: 0, on: false };
    var view = { s: 1, ox: 0, oy: 0, dpr: 1 };

    function resize() {
      var r = canvas.getBoundingClientRect();
      var dpr = Math.min(global.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.round(r.width * dpr));
      canvas.height = Math.max(1, Math.round(r.height * dpr));
      var s = Math.max(r.width / LW, r.height / LH);
      view = { s: s, ox: (r.width - LW * s) / 2, oy: (r.height - LH * s) / 2, dpr: dpr };
    }
    function toLogical(e) {
      var r = canvas.getBoundingClientRect();
      return { x: (e.clientX - r.left - view.ox) / view.s, y: (e.clientY - r.top - view.oy) / view.s };
    }

    function wave(X, Z) {
      var y = 34 * Math.sin(X * 0.0035 + t * 0.0007) + 26 * Math.sin(Z * 0.0045 - t * 0.0009) + 18 * Math.sin((X + Z) * 0.0026 + t * 0.0005);
      for (var i = 0; i < ripples.length; i++) {
        var r = ripples[i], d = Math.hypot(X - r.x, Z - r.z);
        if (d < r.age * 0.55) y += 70 * Math.exp(-r.age * 0.0006) * Math.exp(-d * 0.0012) * Math.sin(d * 0.018 - r.age * 0.009);
      }
      return y;
    }

    function frame(dt) {
      px += ((mouse.on ? (mouse.x - LW / 2) * -0.08 : 0) - px) * 0.06;
      var cx = LW / 2 + px, hy = 330, f = 720, cam = 250, Z0 = 240, Z1 = 2800, XR = 3000;

      nextRipple -= dt;
      if (nextRipple <= 0) { ripples.push({ x: (Math.random() * 2 - 1) * 1400, z: 500 + Math.random() * 1200, age: 0 }); nextRipple = 4500; }
      for (var i = 0; i < ripples.length; i++) ripples[i].age += dt;
      ripples = ripples.filter(function (r) { return r.age < 7000; });

      ctx.setTransform(view.dpr, 0, 0, view.dpr, 0, 0);
      ctx.fillStyle = cfg.background;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.setTransform(view.dpr * view.s, 0, 0, view.dpr * view.s, view.dpr * view.ox, view.dpr * view.oy);

      for (var r = 0; r < rows; r++) {
        var u = r / (rows - 1), Z = Z0 + (Z1 - Z0) * Math.pow(u, 1.6);
        for (var k = 0; k < cols; k++) {
          var X = -XR + 2 * XR * k / (cols - 1), Y = wave(X, Z), q = pts[r * cols + k];
          q.X = X; q.Z = Z; q.Y = Y; q.x = cx + X * f / Z; q.y = hy + (cam - Y) * f / Z;
        }
      }

      ctx.lineWidth = 0.8;
      for (r = rows - 1; r >= 0; r--) {
        u = r / (rows - 1);
        var al = Math.pow(1 - u, 1.3) * 0.42 + 0.04;
        ctx.strokeStyle = rgba(cfg.accent, al);
        ctx.beginPath();
        for (k = 0; k < cols; k++) { q = pts[r * cols + k]; if (k === 0) ctx.moveTo(q.x, q.y); else ctx.lineTo(q.x, q.y); }
        if (r < rows - 1) for (k = 0; k < cols; k++) { var a = pts[r * cols + k], b = pts[(r + 1) * cols + k]; ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); }
        ctx.stroke();
        for (k = 0; k < cols; k++) {
          q = pts[r * cols + k];
          if (q.x < -10 || q.x > LW + 10 || q.y < -10 || q.y > LH + 10) continue;
          var hot = q.Y > 52;
          ctx.fillStyle = rgba(hot ? cfg.warm : cfg.accent, hot ? 0.9 : Math.min(1, al + 0.25));
          ctx.beginPath(); ctx.arc(q.x, q.y, 0.6 + (1 - u) * 2.2, 0, 6.283); ctx.fill();
        }
      }
    }

    function loop(ts) {
      if (dead) return;
      var raw = last ? Math.min(50, ts - last) : 16; last = ts;
      var dt = reduce ? 0 : raw * cfg.speed;
      t += dt;
      frame(dt);
      raf = global.requestAnimationFrame(loop);
    }

    function onMove(e) { var p = toLogical(e); mouse.x = p.x; mouse.y = p.y; mouse.on = true; }
    function onLeave() { mouse.on = false; }
    function onClick(e) {
      if (e.target !== canvas) return;          // ignore clicks on the form
      var p = toLogical(e), best = null, bd = 1e9;
      for (var i = 0; i < pts.length; i++) { var d = Math.hypot(pts[i].x - p.x, pts[i].y - p.y); if (d < bd) { bd = d; best = pts[i]; } }
      if (best) ripples.push({ x: best.X, z: best.Z, age: 0 });
    }

    var ro = global.ResizeObserver ? new ResizeObserver(resize) : null;
    if (ro) ro.observe(canvas); else global.addEventListener('resize', resize);
    global.addEventListener('pointermove', onMove, { passive: true });
    document.addEventListener('pointerleave', onLeave);
    global.addEventListener('click', onClick);
    resize();
    raf = global.requestAnimationFrame(loop);

    return {
      destroy: function () {
        dead = true;
        global.cancelAnimationFrame(raf);
        if (ro) ro.disconnect(); else global.removeEventListener('resize', resize);
        global.removeEventListener('pointermove', onMove);
        document.removeEventListener('pointerleave', onLeave);
        global.removeEventListener('click', onClick);
      },
      set: function (k, v) { cfg[k] = v; }
    };
  }

  global.ThinkubeTerrain = { mount: mount };

  function auto() {
    var els = document.querySelectorAll('canvas[data-tk-terrain]');
    for (var i = 0; i < els.length; i++) mount(els[i]);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', auto);
  else auto();
})(window);
