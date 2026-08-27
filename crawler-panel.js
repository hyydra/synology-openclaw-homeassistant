const panel = document.querySelector("#crawlerPanel");

if (panel) {
  const apiBase = panel.dataset.apiBase;
  const statusEl = document.querySelector("#crawlerStatus");
  const startButton = document.querySelector("#crawlerStartButton");
  const stopButton = document.querySelector("#crawlerStopButton");
  const statsEl = document.querySelector("#crawlerStats");
  const logEl = document.querySelector("#crawlerLog");

  function renderStatus(data) {
    statusEl.textContent = data.running ? "Running" : "Stopped";
    statusEl.className = "crawler-status " + (data.running ? "crawler-status--running" : "crawler-status--stopped");
    startButton.disabled = data.running;
    stopButton.disabled = !data.running;

    const stats = data.stats || {};
    statsEl.textContent = `${stats.discovered || 0} discovered · ${stats.uploaded || 0} uploaded · ${stats.pages_crawled || 0} pages`;

    const logs = data.logs || [];
    logEl.innerHTML = logs.slice().reverse().slice(0, 20).map((log) =>
      `<div class="crawler-log-entry crawler-log-entry--${log.level}">${log.time} ${log.message}</div>`
    ).join("");
  }

  async function pollStatus() {
    try {
      const response = await fetch(`${apiBase}/api/status`);
      if (!response.ok) return;
      renderStatus(await response.json());
    } catch (error) {
      statusEl.textContent = "Unreachable";
      statusEl.className = "crawler-status crawler-status--stopped";
    }
  }

  startButton.addEventListener("click", async () => {
    startButton.disabled = true;
    try {
      await fetch(`${apiBase}/api/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
    } catch (error) {
      startButton.disabled = false;
    }
  });

  stopButton.addEventListener("click", async () => {
    stopButton.disabled = true;
    try {
      await fetch(`${apiBase}/api/stop`, { method: "POST" });
    } catch (error) {
      // Status poll will reconcile the button state on the next tick.
    }
  });

  pollStatus();
  setInterval(pollStatus, 2000);
}
