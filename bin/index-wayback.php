<?php

declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    fwrite(STDERR, "Ez a script csak CLI-ból futtatható.\n");
    exit(1);
}

require_once dirname(__DIR__) . '/lib/archive.php';

$configPath = dirname(__DIR__) . '/config/sources.php';
$archiveBaseDir = dirname(__DIR__) . '/data/archive';
$db = retroArchiveDatabase();
retroEnsureArchiveSchema($db);
$sources = retroLoadSources($configPath);

$indexed = 0;
$skipped = 0;
$failed = 0;

foreach ($sources as $source) {
    $domain = $source['domain'];
    $limit = $source['limit'];
    fwrite(STDOUT, "[{$domain}] CDX lista lekérése...\n");

    $cdx = retroHttpGet(retroBuildCdxUrl($domain, $limit), 3, 15);
    if (!$cdx['ok']) {
        fwrite(STDERR, "[{$domain}] CDX hiba HTTP {$cdx['status']}: {$cdx['error']}\n");
        $failed++;
        continue;
    }

    $rows = json_decode($cdx['body'], true);
    if (!is_array($rows) || count($rows) < 2) {
        fwrite(STDOUT, "[{$domain}] Nincs feldolgozható snapshot.\n");
        continue;
    }

    foreach (array_slice($rows, 1) as $row) {
        if (!is_array($row) || count($row) < 6) {
            $failed++;
            continue;
        }
        [$timestamp, $original] = $row;
        $timestamp = (string) $timestamp;
        $original = (string) $original;

        if (!preg_match('/^\d{14}$/', $timestamp) || $original === '') {
            $failed++;
            continue;
        }
        if (retroSnapshotExists($db, $original, $timestamp)) {
            $skipped++;
            continue;
        }

        $fetchUrl = retroWaybackUrl($timestamp, $original, true);
        fwrite(STDOUT, "[{$domain}] {$timestamp} {$original}\n");
        $snapshot = retroHttpGet($fetchUrl, 3, 20);
        if (!$snapshot['ok'] || trim($snapshot['body']) === '') {
            fwrite(STDERR, "  hiba HTTP {$snapshot['status']}: {$snapshot['error']}\n");
            $failed++;
            usleep(150000);
            continue;
        }

        try {
            retroStoreSnapshot($db, [
                'domain' => $domain,
                'original' => $original,
                'timestamp' => $timestamp,
                'archiveUrl' => retroWaybackUrl($timestamp, $original, false),
            ], $snapshot['body'], $archiveBaseDir);
            $indexed++;
        } catch (Throwable $error) {
            fwrite(STDERR, "  mentési hiba: {$error->getMessage()}\n");
            $failed++;
        }

        usleep(150000);
    }
}

fwrite(STDOUT, "\nKész. Indexelt: {$indexed}, kihagyott: {$skipped}, hibás: {$failed}\n");
