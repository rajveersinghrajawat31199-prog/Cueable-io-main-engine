/* film.js — the SCORE for a UI-morph loop. All timing (beats), geometry and content live here;
 * index.html only holds the layer markup. Demo brand "Northwind" is fictional and all numbers are ILLUSTRATIVE. */
(function () {
  const M = window.HFMorph;
  const CX = 540, CY = 900;               // stage centre; the shape morphs around it
  const INK = "#101613", PAPER = "#FFFFFF", ACCENT = "#2B59FF";

  window.FILM = {
    id: "ui-morph", w: 1080, h: 1920, dur: 16, bpm: 120, fps: 60,   // 8 bars x 4 beats @120 = 16 s = 32 beats
    stage: { cx: CX, cy: CY, bg: "#E9EDE8" },

    // ---- state list on the beat grid: the shape is ONE element, each state is a target -------------------------
    states: [
      { id: "logo",    beat: 0,  w: 240, h: 240, r: 120, fill: ACCENT, pulse: 0.07 },
      { id: "cta",     beat: 1,  w: 700, h: 170, r: 85,  fill: INK,   sfx: [{ dt: 0.05, name: "pop", vol: 0.3 }] },
      { id: "email",   beat: 3,  w: 820, h: 170, r: 44,  fill: PAPER, sfx: [{ dt: 0.05, name: "slide2", vol: 0.2 }].concat([0, 1, 2, 3, 4, 5].map((k) => ({ dt: 0.4 + (3 * k) / 15.5, name: "tick", vol: 0.16 }))) },   // typing ticks: every 3rd char
      { id: "loader",  beat: 7,  w: 170, h: 170, r: 85,  fill: PAPER, sfx: [{ dt: 0.05, name: "tap", vol: 0.25 }] },
      { id: "check",   beat: 9, w: 170, h: 170, r: 85,  fill: ACCENT, pulse: 0.09, sfx: [{ dt: 0.15, name: "toggle", vol: 0.3 }] },
      { id: "dash",    beat: 11, w: 900, h: 720, r: 56,  fill: PAPER, sfx: [{ dt: 0.05, name: "slide2", vol: 0.2 }, { dt: 0.3, name: "up", vol: 0.22 }, { dt: 1.0, name: "pop2", vol: 0.25 }] },
      { id: "chart",   beat: 15, w: 940, h: 800, r: 56,  fill: PAPER, sfx: [{ dt: 0.05, name: "slide1", vol: 0.2 }, { dt: 0.3, name: "slide3", vol: 0.16 }, { dt: 1.5, name: "pop", vol: 0.3 }] },
      { id: "palette", beat: 19, w: 860, h: 560, r: 44,  fill: PAPER, sfx: [{ dt: 0.05, name: "slide2", vol: 0.2 }, { dt: 1.0, name: "select", vol: 0.25 }, { dt: 2.0, name: "select", vol: 0.25 }] },
      { id: "toast",   beat: 25, w: 780, h: 140, r: 70,  fill: INK, pulse: 0.045, sfx: [{ dt: 0.15, name: "toggle", vol: 0.3 }] },
      { id: "logoEnd", beat: 28, w: 240, h: 240, r: 120, fill: ACCENT, layer: "logo", pulse: 0.07, sfx: [{ dt: 0.05, name: "slide3", vol: 0.2 }] },   // == state 0  -> seamless loop
    ],

    // ---- cursor: every USER change is a click; `arrive` = beat by which the tip is on target ---------------------
    cursor: {
      size: 130, tip: [4, 2], lead: 0.16, clickSfx: ["click", "click2", "click", "click"],
      clicks: [3, 7, 15, 25],               // each click lands 0.16 s before the beat that morphs the shape
      path: [
        { x: 620, y: 2150 },                                        // parked off-screen (resting pose IS off-screen)
        { arrive: 2.6, x: 548, y: 912 },                            // CTA
        { beat: 3.6, x: 790, y: 1130 },                             // drift aside while the email types
        { arrive: 6.55, x: 865, y: 905, preset: "snappy" },         // submit arrow
        { beat: 7.6, x: 820, y: 1260 },                             // aside during loader / check
        { beat: 11.6, x: 900, y: 1330 },
        { arrive: 14.55, x: 867, y: 614, preset: "snappy" },        // "Trend" segment
        { beat: 15.5, x: 950, y: 760 },                             // to the last point of the line
        { beat: 18.6, x: 900, y: 1400 },
        { beat: 20.5, x: 840, y: 1360 },
        { beat: 22.2, x: 700, y: 1300 },
        { arrive: 24.5, x: 600, y: 1035, preset: "snappy" },        // "Export report"
        { beat: 25.4, x: 620, y: 2150, preset: "default" },         // leaves the frame (== start pose)
      ],
    },

    // ---- content of each state: pure functions of local time lt (and absolute t) ---------------------------------
    layers: (function () {
      const $ = (id) => document.getElementById(id);
      const cache = {}; const el = (id) => cache[id] || (cache[id] = $(id));
      const fmt = (n) => Math.round(n).toLocaleString("en-US");
      const bump = (dt) => (dt < 0 || dt > 0.45 ? 0 : Math.sin((Math.PI * dt) / 0.45) * Math.exp(-dt * 3));
      const smooth = (x) => (x < 0.5 ? 2 * x * x : 1 - 2 * (1 - x) * (1 - x));

      // one-time geometry
      const DATA = [0.3, 0.42, 0.36, 0.55, 0.5, 0.7, 0.66, 0.88];
      const PTS = DATA.map((v, i) => [60 + i * (820 / 7), 700 - v * 520]);
      function smoothPath(p) {  // Catmull-Rom -> cubic Bezier
        let d = `M${p[0][0]} ${p[0][1]}`;
        for (let i = 0; i < p.length - 1; i++) {
          const p0 = p[i - 1] || p[i], p1 = p[i], p2 = p[i + 1], p3 = p[i + 2] || p2;
          d += ` C${p1[0] + (p2[0] - p0[0]) / 6} ${p1[1] + (p2[1] - p0[1]) / 6} ${p2[0] - (p3[0] - p1[0]) / 6} ${p2[1] - (p3[1] - p1[1]) / 6} ${p2[0]} ${p2[1]}`;
        }
        return d;
      }
      let built = false, lineLen = 0;
      function build() {
        if (built) return; built = true;
        const bars = $("bars");
        for (let i = 0; i < 7; i++) { const b = document.createElement("div"); b.className = "b" + (i === 6 ? " hot" : ""); b.style.left = (i * 118.67).toFixed(2) + "px"; b.style.height = "0px"; bars.appendChild(b); }
        const g = $("grid");
        for (let i = 0; i < 4; i++) g.insertAdjacentHTML("beforeend", `<line x1="60" x2="880" y1="${700 - i * 173}" y2="${700 - i * 173}"/>`);
        const d = smoothPath(PTS);
        $("line").setAttribute("d", d);
        $("area").setAttribute("d", d + ` L${PTS[PTS.length - 1][0]} 700 L${PTS[0][0]} 700 Z`);
        lineLen = $("line").getTotalLength();
        $("line").style.strokeDasharray = lineLen;
        $("endDot").setAttribute("cx", PTS[7][0]); $("endDot").setAttribute("cy", PTS[7][1]);
        const tip = $("tip"); tip.style.right = 940 - (PTS[7][0] + 40) + "px"; tip.style.top = PTS[7][1] - 100 + "px";
      }

      return {
        logo(lt) { build(); el("logoDot").style.transform = `scale(${(1 + 0.45 * bump(lt - 0.5)).toFixed(4)})`; },   // pulse on beat 1

        cta() {},

        email(lt, api, _e, t) {
          const s = api.typed("maya@northwind.co", api.q(lt), 0.4, 15.5);                                                 // types b3.4 -> b6
          el("emailTyped").textContent = s;
          el("caret").style.opacity = s.length < 17 || Math.floor(lt * 4) % 2 === 0 ? 1 : 0;
          el("emailGo").style.transform = `scale(${(1 - 0.14 * api.press(t, api.clickT[1])).toFixed(4)})`;
        },

        loader(lt) { el("spin").style.transform = `rotate(${(lt * 540).toFixed(2)}deg)`; },

        check(lt, api) {
          const g = api.sp(lt - 0.15, "snappy");
          el("checkPath").style.strokeDasharray = 80; el("checkPath").style.strokeDashoffset = (80 * (1 - g)).toFixed(3);
        },

        dash(lt, api, _e, t) {
          build();
          el("dashNum").textContent = "$" + fmt(48290 * api.sp(api.q(lt) - 0.25, "heavy"));
          const bars = el("bars").children, vals = [0.35, 0.5, 0.45, 0.65, 0.58, 0.8, 1.0];
          for (let i = 0; i < 7; i++) bars[i].style.height = (230 * vals[i] * api.sp(lt - (0.5 + i * 0.06), "default")).toFixed(2) + "px";   // bars start on beat 14
          const dp = api.sp(lt - 1.0, "playful");                                                                    // delta pops on beat 15
          el("dashDelta").style.opacity = dp > 0.001 ? 1 : 0; el("dashDelta").style.transform = `scale(${Math.max(0, dp).toFixed(4)})`;
          const ind = api.indicator(t, [[0, 8], [api.clickT[2], 158]], 150);                                        // stretches on the click
          el("segHi").style.left = ind.left + "px"; el("segHi").style.width = ind.right - ind.left + "px";
        },

        chart(lt, api) {
          build();
          const g = smooth(api.clamp((lt - 0.25) / 1.15));                                                          // line draws b17.5 -> b19.5
          el("line").style.strokeDashoffset = (lineLen * (1 - g)).toFixed(2);
          el("area").style.opacity = (g * g).toFixed(3);
          el("grid").style.opacity = api.sp(lt - 0.05, "default").toFixed(3);
          const dd = api.sp(lt - 1.35, "playful"); el("endDot").style.transformOrigin = `${PTS[7][0]}px ${PTS[7][1]}px`; el("endDot").style.transform = `scale(${Math.max(0, dd).toFixed(4)})`;
          const pg = lt - 1.0, ping = el("ping");                                                                     // ripple from the end point on beat 19
          ping.setAttribute("cx", PTS[7][0]); ping.setAttribute("cy", PTS[7][1]);
          ping.setAttribute("r", (16 + 70 * api.clamp(pg / 0.5)).toFixed(2)); ping.style.opacity = (pg > 0 && pg < 0.5 ? 0.55 * (1 - pg / 0.5) : 0).toFixed(3);
          const tp = api.sp(lt - 1.5, "playful");                                                                    // tooltip on beat 20
          el("tip").style.opacity = tp > 0.001 ? 1 : 0; el("tip").style.transform = `scale(${Math.max(0, tp).toFixed(4)})`;
        },

        palette(lt, api, _e, t) {
          const rows = document.querySelectorAll(".pRow");
          rows.forEach((r, i) => { const s = api.sp(lt - (0.2 + i * 0.08), "default"); r.style.opacity = s.toFixed(3); r.style.transform = `translateY(${(26 * (1 - s)).toFixed(2)}px)`; });
          const hi = api.indicator(t, [[0, 160], [api.T(21), 260], [api.T(23), 360]], 100);                          // arrow keys on beats 21, 23
          el("palHi").style.top = hi.left + "px"; el("palHi").style.height = hi.right - hi.left + "px";
          el("palHi").style.opacity = api.sp(lt - 0.3, "default").toFixed(3);
        },

        toast(lt, api) {
          const s = api.sp(lt - 0.15, "playful");
          el("toastIc").style.transform = `scale(${Math.max(0, s).toFixed(4)})`;
        },
      };
    })(),
  };

  window.__film = M.build(window.FILM);
})();
