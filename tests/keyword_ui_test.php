<?php

declare(strict_types=1);

$index = file_get_contents(__DIR__ . '/../index.php');
$app = file_get_contents(__DIR__ . '/../app.js');

if (!is_string($index) || !is_string($app)) {
    fwrite(STDERR, "FAIL: UI files missing\n");
    exit(1);
}

$description = 'Keress kulcsszavakra Pécs és környéke archivált weboldalain. A találatok a Wayback Machine-ből helyben indexelt oldalak szövegében keresnek.';
foreach (['id="query"', 'Kulcsszavas keresés', $description] as $needle) {
    if (!str_contains($index, $needle)) {
        fwrite(STDERR, "FAIL: index missing {$needle}\n");
        exit(1);
    }
}
if (str_contains($index, 'example.com/*')) {
    fwrite(STDERR, "FAIL: URL placeholder remains\n");
    exit(1);
}
foreach (['action=search&q=', 'item.title', 'item.domain', 'item.snippet', 'item.archiveUrl', 'textContent'] as $needle) {
    if (!str_contains($app, $needle)) {
        fwrite(STDERR, "FAIL: app missing {$needle}\n");
        exit(1);
    }
}
if (str_contains($app, 'target = `https://${target}`')) {
    fwrite(STDERR, "FAIL: app still turns keywords into URLs\n");
    exit(1);
}

fwrite(STDOUT, "PASS\n");
