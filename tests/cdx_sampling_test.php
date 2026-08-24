<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/archive.php';

$url = retroBuildCdxUrl('pecs.hu', 150);

foreach ([
    'url=pecs.hu%2F%2A',
    'output=json',
    'collapse=timestamp%3A6',
    'limit=150',
    'filter=statuscode%3A200',
    'filter=mimetype%3Atext%2Fhtml',
] as $needle) {
    if (!str_contains($url, $needle)) {
        fwrite(STDERR, "FAIL: CDX sampling missing {$needle}\n");
        exit(1);
    }
}

if (str_contains($url, 'collapse=digest')) {
    fwrite(STDERR, "FAIL: digest-only collapse keeps too many nearby snapshots\n");
    exit(1);
}

fwrite(STDOUT, "PASS\n");
