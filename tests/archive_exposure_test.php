<?php

declare(strict_types=1);

$htaccess = file_get_contents(__DIR__ . '/../data/.htaccess');
$gitignore = file_get_contents(__DIR__ . '/../.gitignore');
$indexer = file_get_contents(__DIR__ . '/../bin/index-wayback.php');

if (!is_string($htaccess) || (!str_contains($htaccess, 'Require all denied') && !str_contains($htaccess, 'Deny from all'))) {
    fwrite(STDERR, "FAIL: data directory must deny direct HTTP access\n");
    exit(1);
}
if (!is_string($gitignore) || !str_contains($gitignore, '/data/archive/')) {
    fwrite(STDERR, "FAIL: raw archive files must be ignored by git\n");
    exit(1);
}
if (!is_string($indexer) || !str_contains($indexer, 'retroArchiveDataDir(') || !str_contains($indexer, "'/archive'")) {
    fwrite(STDERR, "FAIL: indexer must store snapshots in the external archive data directory\n");
    exit(1);
}

fwrite(STDOUT, "PASS\n");
