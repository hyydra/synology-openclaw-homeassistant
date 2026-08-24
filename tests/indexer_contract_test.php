<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/archive.php';

$url = retroBuildCdxUrl('pecs.hu', 999);
foreach (['url=pecs.hu%2F%2A', 'output=json', 'limit=200', 'filter=statuscode%3A200', 'filter=mimetype%3Atext%2Fhtml'] as $needle) {
    if (!str_contains($url, $needle)) {
        fwrite(STDERR, "FAIL: CDX URL missing {$needle}\n");
        exit(1);
    }
}

$indexer = file_get_contents(__DIR__ . '/../bin/index-wayback.php');
if (!is_string($indexer)) {
    fwrite(STDERR, "FAIL: indexer missing\n");
    exit(1);
}
foreach (['config/sources.php', 'retroStoreSnapshot', 'retroSnapshotExists'] as $needle) {
    if (!str_contains($indexer, $needle)) {
        fwrite(STDERR, "FAIL: indexer contract missing {$needle}\n");
        exit(1);
    }
}
if (str_contains($indexer, 'retroStartSession')) {
    fwrite(STDERR, "FAIL: CLI indexer must not depend on browser session\n");
    exit(1);
}

fwrite(STDOUT, "PASS\n");
