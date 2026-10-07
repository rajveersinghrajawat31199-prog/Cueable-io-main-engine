/*
 * Hairline driver for HyperFrames: makes the pointer-driven figures seek-safe.
 *
 * The stock figures run on requestAnimationFrame, performance.now, setTimeout and
 * live pointer events, so a renderer that jumps to frame N would see wall-clock
 * noise. This driver runs the figures on ONE virtual clock and replays a scripted
 * pointer path against it, in fixed 1/60 s steps. Same seek(t) => same drawing.
 *
 * Globals are swapped only while the driver itself steps/mounts/destroys, then
 * restored, so GSAP and the HyperFrames runtime never see the virtual clock.
 *
 *   const H = Hairline.scene();
 *   H.add("#fig1", "terrain", { intensity: 0.8, theme: "dark",
 *     path: [{ t: 0.5, x: 0.2, y: 0.6 }, { t: 2, x: 0.8, y: 0.4 }, { t: 3, leave: true }] });
 *   H.bind(tl);              // tl = the composition's paused GSAP timeline
 *
 * path: keyframes in seconds; x,y are 0..1 of the figure box. Between keys the
 * pointer eases (smoothstep). `leave: true` takes the pointer off the figure.
 * Before the first key the pointer is off the figure (rest pose).
 * opts.at (seconds) offsets the whole path on the timeline.
 */
import * as figures from "../lib/index.js";

const STEP = 1000 / 60;
const real = {};

function virtualClock() {
  let now = 0, seq = 1e9;
  let rafs = new Map();
  const timers = new Map();
  const api = {
    get now() { return now; },
    raf: (cb) => { const id = ++seq; rafs.set(id, cb); return id; },
    caf: (id) => { rafs.delete(id); },
    st: (cb, ms = 0, ...a) => { const id = ++seq; timers.set(id, { at: now + Math.max(0, ms), cb, a }); return id; },
    ct: (id) => { timers.delete(id); },
    reset() { now = 0; rafs = new Map(); timers.clear(); },
    advance(ms) {
      const target = now + ms;
      for (;;) {
        let nx = null, nid = 0;
        for (const [id, t] of timers) if (t.at <= target && (!nx || t.at < nx.at)) { nx = t; nid = id; }
        if (!nx) break;
        now = nx.at; timers.delete(nid);
        try { nx.cb(...nx.a); } catch (e) { queueMicrotask(() => { throw e; }); }
      }
      now = target;
      const due = rafs; rafs = new Map();
      for (const cb of due.values()) { try { cb(now); } catch (e) { queueMicrotask(() => { throw e; }); } }
    },
  };
  return api;
}

function withClock(clock, fn) {
  const w = window;
  real.now = performance.now; real.raf = w.requestAnimationFrame; real.caf = w.cancelAnimationFrame;
  real.st = w.setTimeout; real.ct = w.clearTimeout; real.io = w.IntersectionObserver;
  performance.now = () => clock.now;
  w.requestAnimationFrame = clock.raf; w.cancelAnimationFrame = clock.caf;
  w.setTimeout = clock.st; w.clearTimeout = clock.ct;
  // Visibility is the scene's job (the clip's data-start/duration), not the observer's.
  w.IntersectionObserver = class { constructor(cb) { this.cb = cb; } observe(el) { this.cb([{ target: el, isIntersecting: true }]); } unobserve() {} disconnect() {} };
  try { return fn(); } finally {
    performance.now = real.now; w.requestAnimationFrame = real.raf; w.cancelAnimationFrame = real.caf;
    w.setTimeout = real.st; w.clearTimeout = real.ct; w.IntersectionObserver = real.io;
  }
}

// One clock for the page's lifetime: the library keeps its rAF handle between mounts.
const CLOCK = virtualClock();

const smooth = (u) => u * u * (3 - 2 * u);

/** Pointer state at time t (seconds, scene-local) from keyframes: {x,y} or null (off the figure). */
function pointerAt(path, t) {
  if (!path.length || t < path[0].t) return null;
  let a = path[0];
  if (a.leave) return null;
  for (let i = 1; i < path.length; i++) {
    const b = path[i];
    if (t < b.t) {
      if (b.leave) return { x: a.x, y: a.y };
      const u = smooth((t - a.t) / Math.max(1e-6, b.t - a.t));
      return { x: a.x + (b.x - a.x) * u, y: a.y + (b.y - a.y) * u };
    }
    if (b.leave) return null;
    a = b;
  }
  return { x: a.x, y: a.y };
}

export function scene() {
  // The stock stylesheet fades stroke/fill with 260 ms CSS transitions: wall-clock, not seekable.
  if (!document.getElementById("hl-seek-safe")) {
    const st = document.createElement("style"); st.id = "hl-seek-safe";
    st.textContent = "[data-hairline] *{transition:none !important}";
    document.head.appendChild(st);
  }
  const items = [];
  let mounted = false, cur = 0; // cur: scene seconds already simulated
  const clock = CLOCK;

  function fire(it, type, p) {
    const r = it.el.getBoundingClientRect();
    const init = { bubbles: true, pointerType: "mouse", pointerId: 1, isPrimary: true };
    if (p) { init.clientX = r.left + p.x * r.width; init.clientY = r.top + p.y * r.height; }
    it.el.dispatchEvent(new PointerEvent(type, init)); // the host element is the stage
  }

  function mountAll() {
    mounted = true; cur = 0;
    withClock(clock, () => {
      // Destroy all first: the library's shared loop must go fully idle (raf=0) so `last` resets.
      for (const it of items) { it.fig?.destroy(); it.fig = null; }
      clock.reset(); // loop is idle now: every fresh replay starts from the same absolute time
      for (const it of items) {
        it.fig = figures[it.name](it.el, { intensity: it.intensity, theme: it.theme, label: it.label });
        it.over = false;
      }
      clock.advance(STEP); // let first draw settle
      cur = STEP / 1000;
    });
  }

  function step(tSec) {
    for (const it of items) {
      const p = pointerAt(it.path, tSec - it.at);
      if (p) {
        it.over = true;
        fire(it, "pointermove", p);
      } else if (it.over) {
        fire(it, "pointerleave", null); it.over = false;
      }
    }
    clock.advance(STEP);
  }

  function seek(t) {
    if (!items.length) return;
    const target = Math.max(0, t);
    if (!mounted || target < cur - 1e-6) mountAll();
    withClock(clock, () => {
      while (cur + STEP / 1000 <= target + 1e-6) { step(cur); cur += STEP / 1000; }
    });
  }

  return {
    add(el, name, opts = {}) {
      if (typeof el === "string") el = document.querySelector(el);
      if (!figures[name]) throw new Error("hairline: unknown figure " + name);
      items.push({ el, name, intensity: opts.intensity ?? 0.5, theme: opts.theme ?? "light", label: opts.label,
        path: (opts.path || []).slice().sort((a, b) => a.t - b.t), at: opts.at ?? 0 });
      mounted = false; // remount on next seek
      return this;
    },
    seek,
    /** Drive from a paused GSAP timeline: one no-op tween whose onUpdate seeks the figures. */
    bind(tl, duration) {
      const d = duration ?? (tl.duration() || 1);
      tl.to({ k: 0 }, { k: 1, duration: d, ease: "none", onUpdate: () => seek(tl.time()) }, 0);
      seek(0);
      return this;
    },
    names: Object.keys(figures),
  };
}

export const names = Object.keys(figures);
