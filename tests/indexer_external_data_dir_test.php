<?php

declare(strict_types=1);

$indexer = file_get_contents(__DIR__ . '/../bin/index-wayback.php');
if (!is_string($indexer)) {
    fwrite(STDERR, "FAIL: indexer missing\n");
    exit(1);
}

foreach (['retroArchiveDataDir(', "'/archive'"] as $needle) {
    if (!str_contains($indexer, $needle)) {
        fwrite(STDERR, "FAIL: indexer archive path must use retroArchiveDataDir\n");
        exit(1);
    }
}

if (str_contains($indexer, "dirname(__DIR__) . '/data/archive'")) {
    fwrite(STDERR, "FAIL: indexer must not hard-code public data/archive\n");
    exit(1);
}

fwrite(STDOUT, "PASS\n");
