<?php

declare(strict_types=1);

require_once __DIR__ . '/auth.php';
retroStartSession();

header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
header('Referrer-Policy: no-referrer');
header("Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'");

$authenticated = retroIsAuthenticated();
?>
<!doctype html>
<html lang="hu">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#10151b">
  <title>Retro kereső | Webarchívum</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/styles.css">
</head>
<body data-authenticated="<?= $authenticated ? 'true' : 'false' ?>">
  <div class="grain"></div>
  <main class="shell">
    <?php if (!$authenticated): ?>
    <section id="loginView" class="login-view" aria-label="Belépés">
      <form id="loginForm" class="login-form">
        <div class="input-row">
          <input id="password" name="password" type="password" autocomplete="current-password" required aria-label="Jelszó" placeholder="••••••••">
          <button class="icon-button" type="submit" aria-label="Belépés">→</button>
        </div>
        <p id="loginError" class="message error" role="alert"></p>
      </form>
    </section>
    <?php else: ?>
    <section id="appView" class="app-view" aria-labelledby="appTitle">
      <header class="topbar">
        <div class="brand"><span class="brand-dot"></span> RETRO / KERESŐ</div>
        <div class="topbar-actions">
          <div class="status"><span class="live-dot"></span> ARCHÍVUM ONLINE</div>
          <button id="logoutButton" class="logout-button" type="button">KIJELENTKEZÉS</button>
        </div>
      </header>
      <div class="hero-copy">
        <p class="eyebrow">WEBARCHÍVUM // WAYBACK MACHINE</p>
        <h1 id="appTitle">Keresd meg,<br><em>ami eltűnt.</em></h1>
        <p class="intro">Írj be egy webcímet, és felfedjük az oldal korábbi változatait.</p>
      </div>
      <form id="searchForm" class="search-form">
        <label for="url">Webcím</label>
        <div class="search-row">
          <span class="protocol">https://</span>
          <input id="url" name="url" type="text" inputmode="url" autocomplete="url" placeholder="example.com/*" required>
          <button class="search-button" type="submit"><span>Keresés</span><b>↗</b></button>
        </div>
        <p class="hint">Használhatsz útvonalat vagy csillagot is, például: <button type="button" class="example-link">index.hu/*</button></p>
        <p id="searchError" class="message error" role="alert"></p>
      </form>
      <section class="results-section" aria-live="polite">
        <div class="results-heading"><h2 id="resultTitle">Találatok</h2><span id="resultCount" class="count"></span></div>
        <div id="results" class="results-grid"></div>
        <div id="emptyState" class="empty-state"><span class="empty-symbol">⌁</span><p>A keresés eredményei itt jelennek meg.</p></div>
      </section>
      <footer class="footer"><span>Az adatokat az Internet Archive biztosítja.</span><a href="https://web.archive.org/" target="_blank" rel="noreferrer">WEB.ARCHIVE.ORG ↗</a></footer>
    </section>
    <?php endif; ?>
  </main>
  <script src="/app.js" type="module"></script>
</body>
</html>
