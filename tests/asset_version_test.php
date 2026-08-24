<?php

declare(strict_types=1);

$index = file_get_contents(__DIR__ . '/../index.php');

function requireAssetVersion(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

requireAssetVersion(strpos($index, 'styles.css?v=') !== false, 'styles.css must be cache-busted');
requireAssetVersion(strpos($index, 'app.js?v=') !== false, 'app.js must be cache-busted');
requireAssetVersion(substr_count($index, 'filemtime(') >= 2, 'asset versions must come from file modification times');

fwrite(STDOUT, "PASS\n");
