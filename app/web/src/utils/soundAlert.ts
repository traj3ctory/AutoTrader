const TONE_FREQUENCIES = [784, 1046.5, 1318.5];
const TONE_STEP_SEC = 0.11;
const TONE_DURATION_SEC = 0.26;
const BURST_OFFSETS_SEC = [0, 0.45];
const TONE_GAIN = 0.42;

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
  for (const burstOffset of BURST_OFFSETS_SEC) {
    TONE_FREQUENCIES.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const start = now + burstOffset + idx * TONE_STEP_SEC;
      osc.type = "triangle";
      osc.frequency.setValueAtTime(freq, start);
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(TONE_GAIN, start + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + TONE_DURATION_SEC);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(start);
      osc.stop(start + TONE_DURATION_SEC + 0.02);
    });
  }

  window.setTimeout(() => {
    void ctx.close();
  }, 1600);
}

export function requestNotificationPermission(): void {
  if (typeof Notification === "undefined") return;
  if (Notification.permission === "default") {
    void Notification.requestPermission();
  }
}

export function sendDesktopNotification({ title, body }: { title: string; body: string }): void {
  if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
  try {
    new Notification(title, { body, tag: "autotrader-signal" });
  } catch {
    // ignore browser notification failures
  }
}
