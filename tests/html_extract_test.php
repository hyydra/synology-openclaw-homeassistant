<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/archive.php';

$html = <<<'HTML'
<!doctype html>
<html lang="hu">
<head>
  <title>Régi Pécs</title>
  <style>.hidden { color:red }</style>
  <script>window.secret = 'SCRIPT-TEXT';</script>
</head>
<body>
  <h1>Pécs története</h1>
  <p>A Zsolnay negyed régi oldala.</p>
  <noscript>NOSCRIPT-TEXT</noscript>
</body>
</html>
HTML;

$page = retroExtractArchivedPage($html);

if (($page['title'] ?? '') !== 'Régi Pécs') {
    fwrite(STDERR, "FAIL: title extraction\n");
    exit(1);
}

$text = $page['text'] ?? '';
if (!str_contains($text, 'Pécs története') || !str_contains($text, 'Zsolnay negyed')) {
    fwrite(STDERR, "FAIL: visible text missing\n");
    exit(1);
}
foreach (['SCRIPT-TEXT', 'NOSCRIPT-TEXT', '.hidden'] as $forbidden) {
    if (str_contains($text, $forbidden)) {
        fwrite(STDERR, "FAIL: non-content text leaked: {$forbidden}\n");
        exit(1);
    }
}

fwrite(STDOUT, "PASS\n");
