/*!
 * HFMorph — seek-safe UI-morph engine for HyperFrames (ui-morph-loop skill).
 *
 * One shape never cuts: it changes size, radius and fill from state to state while each state's
 * content layer swaps behind a short blur. A cursor drives every user-initiated change. Everything is a
 * PURE FUNCTION OF TIME t (closed-form springs, no timers, no Math.random, no state carried between
 * frames), so any frame renders identically and a fix is an edit + re-render.
 *
 * How it plugs into HyperFrames: ONE paused GSAP timeline with a single linear proxy tween whose onUpdate
 * calls render(t). GSAP only supplies the clock; all motion is computed here. index.html registers the returned
 * timeline: window.__timelines[FILM.id] = window.__film.timeline.
 *
 * Contract (window.FILM, authored in film.js):
 *   id, w, h, dur, bpm, offset?, stage:{cx,cy,bg}, ui:{...css vars}
 *   states:[{id, layer?, beat, w,h,r, fill, x?,y?, shadow?, size?:preset, radius?:preset, fillP?:preset}]
 *   cursor:{size, tip:[4,2], fill, stroke, lead, path:[{arrive|beat, x,y, preset?}], clicks:[beat]}
 *   camera?:[{beat, scale, x, y, preset?}]
 *   layers:{ <layerId>: (lt, api) => void }   // draw the content of a state, lt = seconds since state start
 *   fps?: output fps (default 60), used by api.q() to snap discrete content to output frames
 *   beats?: window.BEATS (from beat_grid.py) — measured beats override the nominal bpm grid
 */
(function () {
  "use strict";

  // ---------- math ----------
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, t) => a + (b - a) * t;

  // Named spring presets (diagram 7 of the course): stiffness k, damping d.
  const PRESETS = {
    snappy: { k: 320, d: 30 }, //  buttons, toggles, leading edges, cursor
    default: { k: 170, d: 26 }, // cards, containers, camera (near critical: no overshoot)
    heavy: { k: 90, d: 20 }, //    big type, logo lockups (overdamped)
    playful: { k: 220, d: 14 }, // mascots, stickers (visible overshoot ~18%)
    trail: { k: 140, d: 22 }, //   trailing edge of a stretching indicator
  };
  const P = (p) => (typeof p === "string" ? PRESETS[p] || PRESETS.default : p || PRESETS.default);

  // Closed-form damped spring 0 -> 1, exact for under-, critically- and over-damped cases.
  function spring(t, k = 170, d = 26) {
    if (t <= 0) return 0;
    const w0 = Math.sqrt(k), z = d / (2 * w0);
    if (z < 0.999) {
      const wd = w0 * Math.sqrt(1 - z * z);
      return 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + ((z * w0) / wd) * Math.sin(wd * t));
    }
    if (z <= 1.001) return 1 - Math.exp(-w0 * t) * (1 + w0 * t);
    const s = w0 * Math.sqrt(z * z - 1), r1 = -z * w0 + s, r2 = -z * w0 - s;
    return 1 - (r2 * Math.exp(r1 * t) - r1 * Math.exp(r2 * t)) / (r2 - r1);
  }
  const sp = (t, preset) => { const p = P(preset); return spring(t, p.k, p.d); };

  // Time for a preset to get within `eps` of 1 and stay there (numeric, cached).
  const _settle = {};
  function settle(preset, eps = 0.01) {
    const p = P(preset), key = p.k + ":" + p.d + ":" + eps;
    if (_settle[key] !== undefined) return _settle[key];
    let last = 0;
    for (let t = 0; t < 6; t += 0.005) if (Math.abs(1 - spring(t, p.k, p.d)) > eps) last = t;
    return (_settle[key] = last + 0.005);
  }

  // Multi-target spring: value at t for keys [[time, value, preset?], ...]. One spring per retarget, each starting at
  // its own time, so motion stays continuous and frame 812 renders without simulating 0..811.
  function track(t, keys, preset) {
    let v = keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      const k = keys[i];
      v += (k[1] - keys[i - 1][1]) * sp(t - k[0], k[2] || preset);
    }
    return v;
  }

  // Stretching indicator: leading edge on a stiffer spring than the trailing edge. stops: [[time, x], ...]
  function indicator(t, stops, width) {
    const lead = track(t, stops, "snappy"), trail = track(t, stops, "trail");
    return { left: Math.min(lead, trail), right: Math.max(lead, trail) + width };
  }

  // Text inside a morphing box: in after the morph starts, out before the next one.
  function swapAlpha(t, tIn, tOut, inDelay = 0.08, inDur = 0.12, outLead = 0.1, outDur = 0.1) {
    const a = tIn === null ? 1 : clamp((t - tIn - inDelay) / inDur);
    const b = tOut === null ? 1 : clamp((tOut - outLead - t) / outDur);
    return Math.min(a, b);
  }

  const loopT = (t, dur) => ((t % dur) + dur) % dur;

  // Deterministic typing: how many characters of str are visible at local time lt.
  const typed = (str, lt, t0, cps = 12) => str.slice(0, Math.max(0, Math.min(str.length, Math.floor((lt - t0) * cps))));

  // 0 -> peak -> 0 over `len` seconds (sin * decay); exactly 0 at dt<=0 and dt>=len
  function bumpCurve(dt, len = 0.45) { return dt <= 0 || dt >= len ? 0 : Math.sin((Math.PI * dt) / len) * Math.exp(-dt * 3); }

  // Cursor / button press: 0..1 (down 0.10 s power2.in, up 0.22 s power2.out), tc = click time.
  function press(t, tc) {
    const dt = t - tc;
    if (dt < 0 || dt > 0.32) return 0;
    if (dt < 0.1) return (dt / 0.1) * (dt / 0.1);
    const x = (dt - 0.1) / 0.22;
    return (1 - x) * (1 - x);
  }

  // ---------- colour ----------
  function hex2rgb(h) {
    h = h.replace("#", "");
    if (h.length === 3) h = h.split("").map((c) => c + c).join("");
    const n = parseInt(h, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  const rgbStr = (c) => `rgb(${c.map((v) => Math.round(clamp(v, 0, 255))).join(",")})`;
  const mixHex = (a, b, s) => { const A = hex2rgb(a), B = hex2rgb(b); return rgbStr(A.map((v, i) => lerp(v, B[i], s))); };

  // ---------- film ----------
  function build(FILM, api2) {
    const W = FILM.w, H = FILM.h, DUR = FILM.dur;
    const stage = Object.assign({ cx: W / 2, cy: H / 2, bg: "#fff" }, FILM.stage);

    // beat grid: measured (window.BEATS.beats, seconds) when present, else nominal bpm grid
    const spb = 60 / FILM.bpm, off = FILM.offset || 0;
    const B = window.BEATS && window.BEATS.beats && window.BEATS.beats.length ? window.BEATS.beats : null;
    function T(beat) {
      if (!B) return off + beat * spb;
      const i = Math.floor(beat), f = beat - i;
      const a = B[Math.min(i, B.length - 1)], b = B[Math.min(i + 1, B.length - 1)];
      return a + (b - a) * f;
    }

    // states -> time
    const S = FILM.states.map((s, i) => Object.assign({ x: 0, y: 0, shadow: 0.12, i }, s, { t: T(s.beat) }));
    S.forEach((s, i) => { s.layerId = s.layer || s.id; s.tEnd = i + 1 < S.length ? S[i + 1].t : null; s.rgb = hex2rgb(s.fill); });

    // channel keys, each retarget carrying the incoming state's preset for that channel
    const ch = (prop, presetProp, def, map) => S.map((s, i) => [i === 0 ? 0 : s.t, map ? map(s) : s[prop], s[presetProp] || def]);
    const K = {
      w: ch("w", "size", "default"), h: ch("h", "size", "default"),
      x: ch("x", "size", "default"), y: ch("y", "size", "default"),
      r: ch("r", "radius", "snappy"), shadow: ch("shadow", "size", "default"),
      cr: ch(null, "fillP", "snappy", (s) => s.rgb[0]), cg: ch(null, "fillP", "snappy", (s) => s.rgb[1]), cb: ch(null, "fillP", "snappy", (s) => s.rgb[2]),
    };

    // ---------- DOM ----------
    const root = document.getElementById("stage");
    const world = document.getElementById("world");
    const shape = document.getElementById("shape");
    const layers = {};
    shape.querySelectorAll(".layer").forEach((el) => { layers[el.dataset.mlayer] = el; });
    // every layer is authored at its state's final size and centred, so the shape can clip it mid-morph
    S.forEach((s) => {
      const el = layers[s.layerId];
      if (!el) throw new Error("missing .layer[data-mlayer=" + s.layerId + "] for state " + s.id);
      if (!el.dataset.sized) { el.style.width = s.w + "px"; el.style.height = s.h + "px"; el.dataset.sized = "1"; }
    });
    root.style.background = stage.bg;

    // cursor
    const C = FILM.cursor || null;
    let cursorEl = null, cKeys = null, clickT = [];
    if (C) {
      cursorEl = document.getElementById("cursor");
      const cp = C.path.map((p) => {
        const pre = p.preset || "snappy";
        // `arrive` = the beat by which the tip is on target (start = arrive - settle time); `beat` = start time
        const t0 = p.arrive !== undefined ? T(p.arrive) - settle(pre) : T(p.beat);
        return { t: t0, x: p.x, y: p.y, pre };
      });
      cKeys = { x: cp.map((p, i) => [i === 0 ? 0 : p.t, p.x, p.pre]), y: cp.map((p, i) => [i === 0 ? 0 : p.t, p.y, p.pre]) };
      clickT = (C.clicks || []).map((b) => T(b) - (C.lead === undefined ? 0.16 : C.lead));
    }
    const camKeys = FILM.camera && FILM.camera.length ? {
      s: FILM.camera.map((k, i) => [i === 0 ? 0 : T(k.beat), k.scale, k.preset || "default"]),
      x: FILM.camera.map((k, i) => [i === 0 ? 0 : T(k.beat), k.x || 0, k.preset || "default"]),
      y: FILM.camera.map((k, i) => [i === 0 ? 0 : T(k.beat), k.y || 0, k.preset || "default"]),
    } : null;

    // Output-frame quantiser. Under subframe motion blur, anything DISCRETE (count-up digits, typed characters) must use q(lt):
    // all subframes of one output frame then show the same text, so it stays sharp instead of double-exposing.
    // +0.12 frame bias: the renderer's capture times are not exact multiples of 1/(fps*sub) (measured up to about 1 ms off at 240 fps), so an exact floor put
    // 1 in 3 group boundaries one subframe late and two different numbers were averaged. The bias keeps every subframe of one output frame in the same bucket.
    const OFPS = FILM.fps || 60, q = (x) => Math.floor(x * OFPS + 0.12) / OFPS;
    const api = { q, spring, sp, track, clamp, lerp, press, typed, indicator, swapAlpha, mixHex, bump: bumpCurve, PRESETS, T, states: S, clickT, film: FILM };

    // ---------- render(t): the whole film as a pure function of time ----------
    function render(t) {
      // shape geometry
      const w = Math.max(1, track(t, K.w)), h = Math.max(1, track(t, K.h));
      const cx = stage.cx + track(t, K.x), cy = stage.cy + track(t, K.y);
      const r = clamp(track(t, K.r), 0, Math.min(w, h) / 2);
      const fill = rgbStr([track(t, K.cr), track(t, K.cg), track(t, K.cb)]);
      const sh = clamp(track(t, K.shadow), 0, 1);
      const st = shape.style;
      st.width = w + "px"; st.height = h + "px";
      st.left = cx - w / 2 + "px"; st.top = cy - h / 2 + "px";
      st.borderRadius = r + "px"; st.background = fill;
      let prAll = 0; for (const c of clickT) prAll = Math.max(prAll, press(t, c));
      // beat pulse: a state with `pulse: amp` bumps the whole shape on every beat inside it (0 at the beat's start and after
      // 0.45 s, so the loop seam and the morph that follows are undisturbed). Gives hold states a heartbeat.
      let pulse = 0;
      for (const s of S) {
        if (!s.pulse || t < s.t || (s.tEnd !== null && t >= s.tEnd)) continue;
        for (let k = Math.ceil(s.beat); k < (s.tEnd === null ? FILM.dur / spb + 1 : S[s.i + 1].beat); k++) pulse = Math.max(pulse, s.pulse * bumpCurve(t - T(k)));
      }
      st.transform = FILM.pressShape === false && !pulse ? "none" : `scale(${((1 + pulse) * (FILM.pressShape === false ? 1 : 1 - 0.035 * prAll)).toFixed(4)})`;
      st.boxShadow = `0 ${Math.round(28 * sh + 6)}px ${Math.round(80 * sh + 10)}px rgba(16,22,19,${(0.22 * sh).toFixed(3)})`;

      // layers: max alpha over every state that uses the layer (first state is "already in", last never leaves = loop-safe)
      const alpha = {}, local = {};
      for (const s of S) {
        const sw = Object.assign({ inDelay: 0.14, inDur: 0.16, outLead: 0.04, outDur: 0.06 }, s.swap);
        const a = swapAlpha(t, s.i === 0 ? null : s.t, s.tEnd, sw.inDelay, sw.inDur, sw.outLead, sw.outDur);
        if (t >= s.t && (s.tEnd === null || t < s.tEnd + 0.001)) local[s.layerId] = t - s.t;
        if (a > (alpha[s.layerId] || 0)) alpha[s.layerId] = a;
      }
      for (const id in layers) {
        const el = layers[id], a = alpha[id] || 0;
        if (a <= 0.001) { el.style.visibility = "hidden"; continue; }
        el.style.visibility = "visible"; el.style.opacity = a.toFixed(3);
        el.style.filter = a < 0.999 ? `blur(${((1 - a) * 8).toFixed(2)}px)` : "none";
        const fn = FILM.layers && FILM.layers[id];
        if (fn) fn(local[id] === undefined ? 0 : local[id], api, el, t);
      }

      // cursor
      if (C) {
        const x = track(t, cKeys.x), y = track(t, cKeys.y);
        const pr = prAll;
        const sz = C.size, tip = C.tip || [4, 2];
        const ox = (tip[0] / 24) * sz, oy = (tip[1] / 24) * sz;
        cursorEl.style.transformOrigin = `${ox}px ${oy}px`;
        cursorEl.style.transform = `translate(${(x - ox).toFixed(2)}px,${(y - oy).toFixed(2)}px) scale(${(1 - 0.16 * pr).toFixed(4)})`;
      }

      // camera
      if (camKeys) {
        const s = track(t, camKeys.s);
        world.style.transformOrigin = `${stage.cx}px ${stage.cy}px`;
        world.style.transform = `translate(${track(t, camKeys.x).toFixed(2)}px,${track(t, camKeys.y).toFixed(2)}px) scale(${s.toFixed(5)})`;
      }
      if (FILM.onFrame) FILM.onFrame(t, api);
    }

    // ---------- loop + build report (read by check_morph.mjs / the critic) ----------
    // sound cues derived from the same score: per-state `sfx:[{dt,name,vol}]` (dt = seconds after the state starts) + one per click
    const cues = [];
    S.forEach((s) => (s.sfx || []).forEach((c) => cues.push({ t: +(s.t + (c.dt || 0)).toFixed(3), name: c.name, vol: c.vol })));
    clickT.forEach((t, i) => cues.push({ t: +t.toFixed(3), name: ((C && C.clickSfx) || [])[i] || "click", vol: 0.4 }));
    cues.sort((x, y) => x.t - y.t);
    const first = S[0], last = S[S.length - 1];
    const lastPre = P(last.size || "default");
    const residual = 1 - spring(DUR - last.t, lastPre.k, lastPre.d);
    const ends = () => { render(0); const a = shape.getBoundingClientRect(); render(DUR); const b = shape.getBoundingClientRect(); return { dw: Math.abs(a.width - b.width), dh: Math.abs(a.height - b.height), dx: Math.abs(a.left - b.left), dy: Math.abs(a.top - b.top) }; };
    const cursorOff = (t) => { if (!C) return true; const x = track(t, cKeys.x), y = track(t, cKeys.y); return x < -C.size || x > W + C.size || y < -C.size || y > H + C.size; };
    const report = {
      cues, states: S.length, dur: DUR, bpm: FILM.bpm, measuredGrid: !!B,
      loop: {
        sameGeometry: ["w", "h", "r", "x", "y"].every((p) => first[p] === last[p]) && first.fill === last.fill,
        sameLayer: first.layerId === last.layerId,
        lastMorphResidual: +residual.toFixed(5), // must be ~0 at t=DUR or the seam pops
        cursorOffscreenAtStart: cursorOff(0), cursorOffscreenAtEnd: cursorOff(DUR - 1e-3),
        endsDelta: ends(),
      },
      offBeatStates: S.filter((s) => Math.abs(s.beat - Math.round(s.beat * 2) / 2) > 1e-9).map((s) => s.id), // states not on a half-beat
      clicksBeforeMorph: (C ? C.clicks : []).every((b) => S.some((s) => Math.abs(s.beat - b) < 1e-9)) || "click without a state change on the same beat",
    };
    window.__morphReport = report;
    if (/[?&]report\b/.test(location.search)) { const pre = document.createElement("pre"); pre.id = "morph-report"; pre.textContent = JSON.stringify(report); document.body.appendChild(pre); }   // read by check_morph.py
    render(0);
    { const m = /[?&]t=([0-9.]+)/.exec(location.search); if (m) render(parseFloat(m[1])); }   // ?t=9.5 paints that instant (used by still.py)

    // ---------- HyperFrames timeline: one linear proxy tween drives render(t) ----------
    const proxy = { t: 0 };
    const tl = gsap.timeline({ paused: true });
    tl.to(proxy, { t: DUR, duration: DUR, ease: "none", onUpdate: () => render(proxy.t) }, 0);
    // NOTE: the page registers it (inline script in index.html) so lint sees `window.__timelines[...]`.
    window.__seek = (t) => render(t); // debug / checker hook (not used by the render)
    return { render, timeline: tl, api, report };
  }

  window.HFMorph = { spring, sp, settle, track, indicator, swapAlpha, loopT, typed, press, bumpCurve, clamp, lerp, mixHex, PRESETS, build };
})();
