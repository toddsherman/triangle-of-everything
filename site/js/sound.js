// Sound for cosmic time, made with Web Audio (no files):
//  - while time plays, a Shepard tone: sine waves an octave apart all gliding upward, each fading in at the
//    bottom and out at the top, so the pitch seems to rise forever
//  - a short pop for each new dot on the triangle, pitched by its mass (heavier sounds lower)
// Browsers only allow audio after a click or key press, so nothing is created until start() or pop() runs from one.

const OCTAVES = 7, F_LOW = 40;          // voices span 40 Hz .. 5 kHz
const RISE = 1 / 8;                     // octaves per second
const SIGMA = 1.1;                      // width of the loudness bell, in octaves
const NORM = SIGMA * Math.sqrt(2 * Math.PI);
const TONE_LEVEL = 0.16, POP_LEVEL = 0.32;
const STORE = "toe-sound-muted";

export function createSound() {
  let ac = null, master, toneBus, popBus, voices = [];
  let playing = false, raf = 0, last = 0, phase = 0, sleep = 0;
  let muted = false;
  try { muted = localStorage.getItem(STORE) === "1"; } catch { /* storage blocked: default to on */ }

  function ensure() {
    if (ac) {
      clearTimeout(sleep);
      if (ac.state === "suspended") ac.resume();
      return true;
    }
    const Ctx = window.AudioContext ?? window.webkitAudioContext;
    if (!Ctx) return false;
    ac = new Ctx();
    master = ac.createGain();
    master.gain.value = muted ? 0 : 1;
    master.connect(ac.destination);
    const comp = ac.createDynamicsCompressor();       // keeps a burst of pops from clipping
    comp.connect(master);
    toneBus = ac.createGain();
    toneBus.gain.value = 0;
    toneBus.connect(comp);
    popBus = ac.createGain();
    popBus.gain.value = POP_LEVEL;
    popBus.connect(comp);
    voices = Array.from({ length: OCTAVES }, () => {
      const o = ac.createOscillator(), g = ac.createGain();
      g.gain.value = 0;
      o.connect(g).connect(toneBus);
      o.start();
      return { o, g, oct: Infinity };
    });
    return true;
  }

  function glide(now) {
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    phase = (phase + dt * RISE) % 1;
    const t = ac.currentTime;
    voices.forEach((v, i) => {
      const oct = (i + phase) % OCTAVES;
      const f = F_LOW * 2 ** oct;
      // a voice that wrapped from the top back to the bottom is silent there, so it can jump
      if (oct < v.oct) v.o.frequency.setValueAtTime(f, t);
      else v.o.frequency.setTargetAtTime(f, t, 0.03);
      v.oct = oct;
      v.g.gain.setTargetAtTime(Math.exp(-((oct - OCTAVES / 2) ** 2) / (2 * SIGMA ** 2)) / NORM, t, 0.03);
    });
    raf = requestAnimationFrame(glide);
  }

  /** Pitch for a log10 mass in kg: the Planck-scale end of the chart rings high, the universe low. */
  const pitch = (logM) => (logM == null ? 660 : 1760 * (110 / 1760) ** Math.min(1, Math.max(0, (logM + 36) / 90)));

  function voice(at, f) {
    const o = ac.createOscillator(), g = ac.createGain();
    o.type = "triangle";
    o.frequency.setValueAtTime(f * 1.8, at);
    o.frequency.exponentialRampToValueAtTime(f, at + 0.07);
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(1, at + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 0.28);
    o.connect(g).connect(popBus);
    o.start(at);
    o.stop(at + 0.3);
  }

  return {
    get muted() { return muted; },
    setMuted(m) {
      muted = m;
      try { localStorage.setItem(STORE, m ? "1" : "0"); } catch { /* not remembered */ }
      if (ac) master.gain.setTargetAtTime(m ? 0 : 1, ac.currentTime, 0.05);
    },
    /** Time started playing: fade the Shepard tone in. */
    start() {
      if (playing || !ensure()) return;
      playing = true;
      toneBus.gain.setTargetAtTime(TONE_LEVEL, ac.currentTime, 0.3);
      last = performance.now();
      raf = requestAnimationFrame(glide);
    },
    /** Time paused: fade the tone out, then let the audio device sleep. */
    stop() {
      if (!playing) return;
      playing = false;
      cancelAnimationFrame(raf);
      toneBus.gain.setTargetAtTime(0, ac.currentTime, 0.12);
      clearTimeout(sleep);
      sleep = setTimeout(() => { if (!playing) ac.suspend(); }, 1500);
    },
    /** New dots: a quick run of pops, one per log10 mass given (the caller keeps it to a few), after delay s. */
    pop(masses, delay = 0) {
      if (muted || !masses.length || !ensure()) return;
      const now = ac.currentTime + delay;
      masses.forEach((m, i) => voice(now + 0.01 + i * 0.045, pitch(m)));
    },
  };
}
