<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/archive.php';

function requireIndexLimit(mixed $actual, mixed $expected, string $label): void
{
    if ($actual !== $expected) {
        fwrite(STDERR, "FAIL: {$label}; expected " . var_export($expected, true) . ', got ' . var_export($actual, true) . "\n");
        exit(1);
    }
}

requireIndexLimit(retroIndexLimitOverride(['index-wayback.php']), null, 'missing option must preserve configured limits');
requireIndexLimit(retroIndexLimitOverride(['index-wayback.php', '--limit=5']), 5, 'explicit limit must override each source');
requireIndexLimit(retroIndexLimitOverride(['index-wayback.php', '--limit=0']), 1, 'limit must be bounded to one');
requireIndexLimit(retroIndexLimitOverride(['index-wayback.php', '--limit=999']), 200, 'limit must be bounded to two hundred');

try {
    retroIndexLimitOverride(['index-wayback.php', '--limit=nope']);
    fwrite(STDERR, "FAIL: malformed limit must be rejected\n");
    exit(1);
} catch (InvalidArgumentException) {
}

fwrite(STDOUT, "PASS\n");
