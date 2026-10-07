/*
 * thinking-orbs driver for HyperFrames.
 *
 * The orb geometry is a pure function of time: MODE_FRAMES[mode](size, t, opts) returns the finished,
 * z-sorted dots. So no virtual clock is needed: seek(t) just draws the frame for t. Same t => same pixels.
 * We replace the library's painter (grey ramp, tied to the page theme) with one that mixes the brand ink
 * into the film's background colour by depth, and add a state timeline with cross-fades.
 *
 *   const O = Orbs.scene();
 *   O.add("#orb", { states: [{t:0,state:"searching"},{t:2.4,state:"solving"},{t:4.8,state:"composing"}],
 *                   size: 64, px: 420, ink: "#ffffff", bg: "#0b0b0e", fade: 0.3 });
 *   O.bind(tl, TOTAL);   // paused GSAP timeline of the composition, call last
 *
 * opts: states[{t,state}] | state; size 64 (avatar tuning) or 20 (inline tuning); px = rendered CSS size;
 * ink = nearest-dot colour; bg = colour far dots fade into (use the scene background); at = time offset (s);
 * speed = multiplier; fade = cross-fade seconds between states;
 * opts = raw engine knobs (e.g. {shape:1} holds the triangle for `shaping`).
 */
import { MODE_FRAMES, resolvePreset } from "../lib/engine.es.js";

const SS = 2; // fixed 2x supersample: deterministic, independent of the render machine's DPR

function hex(c) {
  c = c.trim().replace("#", "");
  if (c.length === 3) c = c.split("").map((x) => x + x).join("");
  return [0, 2, 4].map((i) => parseInt(c.slice(i, i + 2), 16));
}
const mixc = (bg, ink, k) => `rgb(${bg.map((b, i) => Math.round(b + (ink[i] - b) * k)).join(",")})`;

function scaled(state, size, _d, _s, extra) {
  const r = resolvePreset(state, size);
  return { mode: r.mode, speed: r.speed, opts: extra ? { ...r.opts, ...extra } : r.opts };
}

function drawFrame(ctx, f, k, ink, bg, alpha) {
  ctx.globalAlpha = alpha;
  ctx.lineCap = "round";
  for (const l of f.lines) {
    ctx.strokeStyle = mixc(bg, ink, 1 - Math.min(1, Math.max(0, l.white)));
    ctx.globalAlpha = alpha * (l.a ?? 1);
    ctx.lineWidth = l.w * k;
    ctx.beginPath(); ctx.moveTo(l.x1 * k, l.y1 * k); ctx.lineTo(l.x2 * k, l.y2 * k); ctx.stroke();
  }
  for (const d of f.dots) {
    ctx.fillStyle = mixc(bg, ink, 1 - Math.min(1, Math.max(0, d.white)));
    ctx.globalAlpha = alpha * (d.a ?? 1);
    ctx.beginPath(); ctx.arc(d.x * k, d.y * k, d.r * k, 0, Math.PI * 2); ctx.fill();
  }
  ctx.globalAlpha = 1;
}

export function scene() {
  const items = [];
  function seek(t) {
    for (const it of items) {
      const lt = Math.max(0, t - it.at);
      let idx = 0;
      for (let i = 0; i < it.states.length; i++) if (lt >= it.states[i].t) idx = i;
      const cur = it.states[idx], prev = idx > 0 ? it.states[idx - 1] : null;
      const ctx = it.ctx, W = it.canvas.width;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, W, W);
      const k = W / it.size;
      const paintState = (st, alpha) => {
        const p = it.cache[st] || (it.cache[st] = scaled(st, it.size, 1, 1, it.extra));
        const frame = MODE_FRAMES[p.mode](it.size, lt * it.speed * p.speed, p.opts);
        drawFrame(ctx, frame, k, it.ink, it.bg, alpha);
      };
      const x = prev && it.fade > 0 ? Math.min(1, (lt - cur.t) / it.fade) : 1;
      if (x < 1) { paintState(prev.state, 1 - x); paintState(cur.state, x); } else paintState(cur.state, 1);
    }
  }
  return {
    add(el, o = {}) {
      if (typeof el === "string") el = document.querySelector(el);
      const size = o.size === 20 ? 20 : 64;
      const px = o.px || 360;
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = px * SS;
      canvas.style.cssText = `width:${px}px;height:${px}px;display:block`;
      canvas.setAttribute("role", "img");
      el.replaceChildren(canvas);
      const states = (o.states || [{ t: 0, state: o.state || "working" }]).slice().sort((a, b) => a.t - b.t);
      items.push({ canvas, ctx: canvas.getContext("2d"), size, states, ink: hex(o.ink || "#ffffff"), bg: hex(o.bg || "#000000"),
        at: o.at || 0, speed: o.speed || 1, fade: o.fade ?? 0.3, extra: o.opts, cache: {} });
      return this;
    },
    seek,
    bind(tl, duration) {
      const d = duration ?? (tl.duration() || 1);
      tl.to({ k: 0 }, { k: 1, duration: d, ease: "none", onUpdate: () => seek(tl.time()) }, 0);
      seek(0);
      return this;
    },
  };
}

export const states = ["working", "searching", "solving", "listening", "connecting", "weaving", "composing", "breathing", "shaping"];
