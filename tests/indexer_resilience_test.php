<?php

declare(strict_types=1);

$indexer = file_get_contents(__DIR__ . '/../bin/index-wayback.php');
if (!is_string($indexer)) {
    fwrite(STDERR, "FAIL: indexer missing\n");
    exit(1);
}

function requireResilience(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

requireResilience(str_contains($indexer, 'retroHttpGetWithRetry'), 'retry helper must be used');
requireResilience(str_contains($indexer, '30'), 'network timeout must allow 30 seconds');
requireResilience(str_contains($indexer, 'sleep($backoffSeconds)'), 'retry backoff must wait between attempts');
requireResilience(str_contains($indexer, '1000000'), 'snapshot pacing must be about one second');
requireResilience(str_contains($indexer, '$consecutiveFailures'), 'domain circuit breaker must track consecutive failures');
requireResilience(str_contains($indexer, '>= 5'), 'domain circuit breaker must stop after repeated failures');

fwrite(STDOUT, "PASS\n");
