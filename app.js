const loginForm = document.querySelector("#loginForm");
const searchForm = document.querySelector("#searchForm");
const loginError = document.querySelector("#loginError");
const searchError = document.querySelector("#searchError");
const results = document.querySelector("#results");
const emptyState = document.querySelector("#emptyState");
const resultCount = document.querySelector("#resultCount");
const resultTitle = document.querySelector("#resultTitle");
const logoutButton = document.querySelector("#logoutButton");

if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.textContent = "";
    const password = new FormData(loginForm).get("password");
    const response = await fetch("/api.php?action=login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      loginError.textContent = data.error || "A belépés nem sikerült.";
      return;
    }

    window.location.reload();
  });
}

if (logoutButton) {
  logoutButton.addEventListener("click", async () => {
    await fetch("/api.php?action=logout", { method: "POST" }).catch(() => {});
    window.location.reload();
  });
}

function formatDate(timestamp) {
  if (!timestamp || timestamp.length < 8) return "ISMERETLEN DÁTUM";
  return `${timestamp.slice(6, 8)}.${timestamp.slice(4, 6)}.${timestamp.slice(0, 4)}`;
}

function renderResults(items) {
  results.replaceChildren();
  resultCount.textContent = `${items.length} TALÁLAT`;
  emptyState.classList.toggle("hidden", items.length > 0);

  if (!items.length) {
    resultTitle.textContent = "Nincs találat";
    emptyState.querySelector("p").textContent = "Nincs találat a helyi archívumban.";
    return;
  }

  resultTitle.textContent = "Találatok";
  for (const item of items) {
    const card = document.createElement("article");
    card.className = "result-card";

    const top = document.createElement("div");
    top.className = "card-top";

    const date = document.createElement("span");
    date.className = "card-date";
    date.textContent = formatDate(item.timestamp);

    const domain = document.createElement("span");
    domain.className = "card-domain";
    domain.textContent = item.domain || "";
    top.append(date, domain);

    const title = document.createElement("h3");
    title.className = "card-title";
    title.textContent = item.title || item.original || "Névtelen oldal";

    const url = document.createElement("div");
    url.className = "card-url";
    url.textContent = item.original || "";

    const snippet = document.createElement("p");
    snippet.className = "card-snippet";
    snippet.textContent = item.snippet || "";

    const link = document.createElement("a");
    link.className = "card-link";
    link.href = item.archiveUrl;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = "MEGNYITÁS A WAYBACKEN ↗";

    card.append(top, title, url, snippet, link);
    results.append(card);
  }
}

if (searchForm) {
  searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    searchError.textContent = "";
    const input = document.querySelector("#query");
    const query = input.value.trim();
    if (!query) return;

    results.replaceChildren();
    emptyState.classList.remove("hidden");
    emptyState.classList.add("loading");
    emptyState.querySelector("p").textContent = "Keresés a helyi archívumban...";
    resultCount.textContent = "";

    try {
      const response = await fetch(`/api.php?action=search&q=${encodeURIComponent(query)}`);
      const data = await response.json();
      if (response.status === 401) {
        window.location.reload();
        return;
      }
      if (!response.ok) throw new Error(data.error || "A keresés sikertelen.");
      renderResults(Array.isArray(data.results) ? data.results : []);
    } catch (error) {
      searchError.textContent = error.message;
      resultTitle.textContent = "Találatok";
      resultCount.textContent = "";
      emptyState.querySelector("p").textContent = "A keresés nem sikerült.";
    } finally {
      emptyState.classList.remove("loading");
    }
  });
}
