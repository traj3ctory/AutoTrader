const TONE_FREQUENCIES = [659.25, 880];
const TONE_STEP_SEC = 0.14;
const TONE_DURATION_SEC = 0.25;
const TONE_GAIN = 0.14;

export function playTradeAlert(): void {
  const AudioCtx =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioCtx) return;

  const ctx = new AudioCtx();
  if (ctx.state === "suspended") {
    void ctx.resume();
  }

  const now = ctx.currentTime;
  TONE_FREQUENCIES.forEach((freq, idx) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const start = now + idx * TONE_STEP_SEC;
    osc.type = "sine";
    osc.frequency.setValueAtTime(freq, start);
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(TONE_GAIN, start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + TONE_DURATION_SEC);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(start);
    osc.stop(start + TONE_DURATION_SEC + 0.02);
  });

  window.setTimeout(() => {
    void ctx.close();
  }, 1000);
}
