<?php

declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    fwrite(STDERR, "Ez a script csak CLI-ból futtatható.\n");
    exit(1);
}

require_once dirname(__DIR__) . '/lib/archive.php';

/** @return array{ok:bool,status:int,body:string,error:string,errno:int} */
function retroHttpGetWithRetry(string $url, int $connectTimeout = 5, int $timeout = 30, int $attempts = 3): array
{
    $attempts = max(1, $attempts);
    $last = ['ok' => false, 'status' => 0, 'body' => '', 'error' => '', 'errno' => 0];

    for ($attempt = 1; $attempt <= $attempts; $attempt++) {
        $last = retroHttpGet($url, $connectTimeout, $timeout);
        if ($last['ok']) {
            return $last;
        }

        if ($attempt < $attempts) {
            $backoffSeconds = 2 ** $attempt;
            fwrite(STDERR, "  hálózati hiba, újrapróbálás {$backoffSeconds} mp múlva ({$attempt}/{$attempts})...\n");
            sleep($backoffSeconds);
        }
    }

    return $last;
}

$projectRoot = dirname(__DIR__);
$configPath = $projectRoot . '/config/sources.php';
$archiveBaseDir = retroArchiveDataDir($projectRoot) . '/archive';
$db = retroArchiveDatabase();
retroEnsureArchiveSchema($db);
$sources = retroLoadSources($configPath);
$limitOverride = retroIndexLimitOverride($argv);

$indexed = 0;
$skipped = 0;
$failed = 0;

foreach ($sources as $source) {
    $domain = $source['domain'];
    $limit = $limitOverride ?? $source['limit'];
    fwrite(STDOUT, "[{$domain}] CDX lista lekérése...\n");

    $cdx = retroHttpGetWithRetry(retroBuildCdxUrl($domain, $limit), 5, 30, 3);
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

    $consecutiveFailures = 0;
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
        if (!retroArchiveUrlIsIndexable($original)) {
            fwrite(STDOUT, "[{$domain}] kihagyva minőségi szűrővel: {$original}\n");
            $skipped++;
            continue;
        }
        if (retroSnapshotExists($db, $original, $timestamp)) {
            $skipped++;
            continue;
        }

        $fetchUrl = retroWaybackUrl($timestamp, $original, true);
        fwrite(STDOUT, "[{$domain}] {$timestamp} {$original}\n");
        $snapshot = retroHttpGetWithRetry($fetchUrl, 5, 30, 3);
        if (!$snapshot['ok'] || trim($snapshot['body']) === '') {
            fwrite(STDERR, "  hiba HTTP {$snapshot['status']}: {$snapshot['error']}\n");
            $failed++;
            $consecutiveFailures++;
            if ($consecutiveFailures >= 5) {
                fwrite(STDERR, "[{$domain}] 5 egymást követő hálózati hiba, a domain feldolgozása megszakad.\n");
                break;
            }
            usleep(1000000);
            continue;
        }

        $consecutiveFailures = 0;
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

        usleep(1000000);
    }
}

fwrite(STDOUT, "\nKész. Indexelt: {$indexed}, kihagyott: {$skipped}, hibás: {$failed}\n");
