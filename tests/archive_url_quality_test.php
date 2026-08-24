<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/archive.php';

function requireArchiveUrlQuality(string $url, bool $expected, string $label): void
{
    $actual = retroArchiveUrlIsIndexable($url);
    if ($actual !== $expected) {
        fwrite(STDERR, "FAIL: {$label}; expected " . ($expected ? 'accepted' : 'rejected') . "\n");
        exit(1);
    }
}

requireArchiveUrlQuality('https://pecs.hu/01-szamu-valasztokerulet/', true, 'normal page');
requireArchiveUrlQuality('https://pecs.hu/%EF%BF%BC/', true, 'encoded object replacement character may still identify valuable content');
requireArchiveUrlQuality("https://pecs.hu/\u{FFFC}/", true, 'decoded object replacement character may still identify valuable content');
requireArchiveUrlQuality('http://pte.hu:80/404', false, '404 path');
requireArchiveUrlQuality('https://example.test/archive/404/details', false, 'nested 404 path segment');
requireArchiveUrlQuality('https://example.test/article-404-history', true, '404 digits inside a valid slug');

fwrite(STDOUT, "PASS\n");
