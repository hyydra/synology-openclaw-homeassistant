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
$stylesVersion = (string) filemtime(__DIR__ . '/styles.css');
$appVersion = (string) filemtime(__DIR__ . '/app.js');
$buildVersion = trim((string) file_get_contents(__DIR__ . '/VERSION'));
?>
<!doctype html>
<html lang="hu">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#f6f6f3">
  <title>Retro kereső</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/styles.css?v=<?= htmlspecialchars($stylesVersion, ENT_QUOTES, 'UTF-8') ?>">
</head>
<body data-authenticated="<?= $authenticated ? 'true' : 'false' ?>">
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
    <section id="appView" class="app-view" aria-label="Archívum kereső">
      <header class="topbar">
        <div class="brand">RETRO KERESŐ</div>
        <button id="logoutButton" class="logout-button" type="button">Kijelentkezés</button>
      </header>

      <form id="searchForm" class="search-form">
        <label for="query">Kulcsszavas keresés</label>
        <p class="search-description">Keress kulcsszavakra Pécs és környéke archivált weboldalain. A találatok a Wayback Machine-ből helyben indexelt oldalak szövegében keresnek.</p>
        <div class="search-row">
          <input id="query" name="query" type="search" autocomplete="off" placeholder="pécs, zsolnay, uránváros…" required>
          <button class="search-button" type="submit">Keresés</button>
        </div>
        <p id="searchError" class="message error" role="alert"></p>
      </form>

      <section class="results-section" aria-live="polite">
        <div class="results-heading">
          <h2 id="resultTitle">Találatok</h2>
          <span id="resultCount" class="count"></span>
        </div>
        <div id="results" class="results-grid"></div>
        <div id="emptyState" class="empty-state"><p>A találatok itt jelennek meg.</p></div>
      </section>
    </section>
    <div class="build-version">
      build <?= htmlspecialchars($buildVersion, ENT_QUOTES, 'UTF-8') ?> · Credits: CDX/Wayback workflow informed by jsvine/waybackpack and hartator/wayback-machine-downloader
    </div>
    <?php endif; ?>
  </main>
  <script src="/app.js?v=<?= htmlspecialchars($appVersion, ENT_QUOTES, 'UTF-8') ?>" type="module"></script>
</body>
</html>
