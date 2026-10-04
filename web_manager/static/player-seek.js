// Small, paced seeks replace the browser's larger repeated arrow-key jumps.
(() => {
  const player = document.getElementById("player");
  const dialog = document.getElementById("playerDialog");
  const hint = document.getElementById("playerSeekHint") || document.createElement("div");
  const idleHint = "按住 ← / → 后退 / 快进 · Ctrl + ← / → 上一个 / 下一个视频";
  if (!hint.id) {
    hint.id = "playerSeekHint";
    hint.className = "player-subtitle";
    document.getElementById("playerSubtitle").after(hint);
  }
  hint.textContent = idleHint;
  let heldKey = null;
  let timer = null;
  let resumePlayback = false;

  function stop(resume = true) {
    window.clearInterval(timer);
    timer = null;
    heldKey = null;
    hint.textContent = idleHint;
    const shouldPlay = resume && resumePlayback && dialog.open;
    resumePlayback = false;
    if (shouldPlay) player.play().catch(() => {});
  }

  function step() {
    // Let the previous seek finish so a slow decoder can still show frames.
    if (player.seeking || player.readyState < 2 || !Number.isFinite(player.duration)) return;
    const direction = heldKey === "ArrowRight" ? 1 : -1;
    player.currentTime = Math.max(0, Math.min(player.duration, player.currentTime + direction * 2.4));
    hint.textContent = `${direction > 0 ? "快进" : "后退"} · ${player.currentTime.toFixed(1)} 秒`;
  }

  document.addEventListener("keydown", (event) => {
    if (!dialog.open || !["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    if (event.ctrlKey || event.altKey || event.metaKey || event.shiftKey) return;
    if (event.target instanceof Element && event.target.closest("input, textarea, select, [contenteditable]:not([contenteditable='false'])")) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (heldKey === event.key) return;
    if (!heldKey) {
      resumePlayback = !player.paused && !player.ended;
      player.pause();
    }
    window.clearInterval(timer);
    heldKey = event.key;
    step();
    timer = window.setInterval(step, 100);
  }, true);

  document.addEventListener("keyup", (event) => {
    if (event.key !== heldKey) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    stop();
  }, true);

  window.addEventListener("blur", () => stop());
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
  });
  dialog.addEventListener("close", () => stop(false));
  player.addEventListener("emptied", () => stop(false));
  player.addEventListener("playernavigate", () => stop());
})();
