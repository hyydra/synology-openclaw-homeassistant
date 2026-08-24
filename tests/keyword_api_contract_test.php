<?php

declare(strict_types=1);

$api = file_get_contents(__DIR__ . '/../api.php');
if (!is_string($api)) {
    fwrite(STDERR, "FAIL: api.php missing\n");
    exit(1);
}

foreach (["require_once __DIR__ . '/lib/archive.php'", "\$_GET['q']", 'retroSearchArchive'] as $needle) {
    if (!str_contains($api, $needle)) {
        fwrite(STDERR, "FAIL: missing keyword API contract: {$needle}\n");
        exit(1);
    }
}
foreach (['web.archive.org/cdx/search/cdx', 'curl_init(', "\$_GET['url']"] as $forbidden) {
    if (str_contains($api, $forbidden)) {
        fwrite(STDERR, "FAIL: live Wayback/browser URL logic remains: {$forbidden}\n");
        exit(1);
    }
}
if (!str_contains($api, 'respond(401')) {
    fwrite(STDERR, "FAIL: auth protection missing\n");
    exit(1);
}

fwrite(STDOUT, "PASS\n");
