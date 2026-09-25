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
 * shifts slightly with the pointer. Honours prefers-reduced-motion (draws one
 * static frame, redrawn only on resize). Scene is authored in a 1440x900
 * logical space and scaled to cover the canvas.
 *
 * Cost limits, so the page stays responsive without GPU acceleration: at most
 * MAX_FPS frames per second; the canvas is drawn at CSS-pixel resolution (the
 * background is soft, so high-DPI sharpness is not needed); dots are filled in
 * a few batched paths per row instead of one fill per dot.
 */
(function (global) {
  'use strict';

  var LW = 1440, LH = 900, MAX_FPS = 30;

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
    var view = { s: 1, ox: 0, oy: 0 };

    // Colour strings per row, built once: row lines, row dots, and wave crests.
    var pal;
    function palette() {
      pal = { line: [], dot: [], hot: rgba(cfg.warm, 0.9) };
      for (var r = 0; r < rows; r++) {
        var al = Math.pow(1 - r / (rows - 1), 1.3) * 0.42 + 0.04;
        pal.line.push(rgba(cfg.accent, al));
        pal.dot.push(rgba(cfg.accent, Math.min(1, al + 0.25)));
      }
    }
    palette();

    function resize() {
      var r = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.round(r.width));
      canvas.height = Math.max(1, Math.round(r.height));
      var s = Math.max(r.width / LW, r.height / LH);
      view = { s: s, ox: (r.width - LW * s) / 2, oy: (r.height - LH * s) / 2 };
      if (reduce) frame(0);
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
      // Ease the pointer parallax at the same speed whatever the frame rate (6% per 16.7 ms).
      px += ((mouse.on ? (mouse.x - LW / 2) * -0.08 : 0) - px) * (1 - Math.pow(0.94, dt / 16.7));
      var cx = LW / 2 + px, hy = 330, f = 720, cam = 250, Z0 = 240, Z1 = 2800, XR = 3000;

      nextRipple -= dt;
      if (nextRipple <= 0) { ripples.push({ x: (Math.random() * 2 - 1) * 1400, z: 500 + Math.random() * 1200, age: 0 }); nextRipple = 4500; }
      for (var i = 0; i < ripples.length; i++) ripples[i].age += dt;
      ripples = ripples.filter(function (r) { return r.age < 7000; });

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = cfg.background;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.setTransform(view.s, 0, 0, view.s, view.ox, view.oy);

      for (var r = 0; r < rows; r++) {
        var u = r / (rows - 1), Z = Z0 + (Z1 - Z0) * Math.pow(u, 1.6);
        for (var k = 0; k < cols; k++) {
          var X = -XR + 2 * XR * k / (cols - 1), Y = wave(X, Z), q = pts[r * cols + k];
          q.X = X; q.Z = Z; q.Y = Y; q.x = cx + X * f / Z; q.y = hy + (cam - Y) * f / Z;
        }
      }

      ctx.lineWidth = 0.8;
      // Rows back to front; per row one stroke for its lines, one fill for its
      // plain dots and one fill for its crest dots.
      for (r = rows - 1; r >= 0; r--) {
        u = r / (rows - 1);
        var rad = 0.6 + (1 - u) * 2.2;
        ctx.strokeStyle = pal.line[r];
        ctx.beginPath();
        for (k = 0; k < cols; k++) { q = pts[r * cols + k]; if (k === 0) ctx.moveTo(q.x, q.y); else ctx.lineTo(q.x, q.y); }
        if (r < rows - 1) for (k = 0; k < cols; k++) { var a = pts[r * cols + k], b = pts[(r + 1) * cols + k]; ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); }
        ctx.stroke();
        for (var pass = 0; pass < 2; pass++) {
          var crest = pass === 1, any = false;
          ctx.beginPath();
          for (k = 0; k < cols; k++) {
            q = pts[r * cols + k];
            if (q.x < -10 || q.x > LW + 10 || q.y < -10 || q.y > LH + 10 || (q.Y > 52) !== crest) continue;
            ctx.moveTo(q.x + rad, q.y); ctx.arc(q.x, q.y, rad, 0, 6.283); any = true;
          }
          if (any) { ctx.fillStyle = crest ? pal.hot : pal.dot[r]; ctx.fill(); }
        }
      }
    }

    function loop(ts) {
      if (dead) return;
      raf = global.requestAnimationFrame(loop);
      if (last && ts - last < 1000 / MAX_FPS - 2) return;   // skip frames above MAX_FPS
      var dt = (last ? Math.min(100, ts - last) : 16) * cfg.speed; last = ts;
      t += dt;
      frame(dt);
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
    resize();
    // Reduced motion: resize() has drawn the static frame; no animation loop or pointer effects.
    if (!reduce) {
      global.addEventListener('pointermove', onMove, { passive: true });
      document.addEventListener('pointerleave', onLeave);
      global.addEventListener('click', onClick);
      raf = global.requestAnimationFrame(loop);
    }

    return {
      destroy: function () {
        dead = true;
        global.cancelAnimationFrame(raf);
        if (ro) ro.disconnect(); else global.removeEventListener('resize', resize);
        global.removeEventListener('pointermove', onMove);
        document.removeEventListener('pointerleave', onLeave);
        global.removeEventListener('click', onClick);
      },
      set: function (k, v) { cfg[k] = v; palette(); if (reduce) frame(0); }
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
