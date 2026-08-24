<?php

declare(strict_types=1);

function loggingContractAssert(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

$api = file_get_contents(__DIR__ . '/../api.php');
$indexer = file_get_contents(__DIR__ . '/../bin/index-wayback.php');

loggingContractAssert(is_string($api), 'api.php should be readable');
loggingContractAssert(is_string($indexer), 'index-wayback.php should be readable');

// Both production entry points must load the shared logger.
loggingContractAssert(str_contains($api, "require_once __DIR__ . '/lib/logger.php';"), 'API should load logger.php');
loggingContractAssert(str_contains($indexer, "require_once dirname(__DIR__) . '/lib/logger.php';"), 'indexer should load logger.php');

// API failures must be logged while browser responses stay generic.
loggingContractAssert(str_contains($api, "retroLog('error', 'archive_search_failed'"), 'archive search failures should be logged');
loggingContractAssert(!str_contains($api, "respond(500, ['error' => $error->getMessage()])"), 'internal exception text must not be returned to clients');
loggingContractAssert(str_contains($api, "header('X-Request-ID: ' . retroRequestId());"), 'API should expose the server request id for support correlation');

// Indexer network and persistence failures must be persisted, not only printed to STDERR.
loggingContractAssert(str_contains($indexer, "retroLog('error', 'cdx_fetch_failed'"), 'CDX failures should be logged');
loggingContractAssert(str_contains($indexer, "retroLog('error', 'snapshot_fetch_failed'"), 'snapshot fetch failures should be logged');
loggingContractAssert(str_contains($indexer, "retroLog('error', 'snapshot_store_failed'"), 'snapshot storage failures should be logged');

fwrite(STDOUT, "PASS\n");
