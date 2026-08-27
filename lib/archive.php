<?php

declare(strict_types=1);

function retroArchiveDataDir(?string $projectRoot = null): string
{
    $projectRoot ??= dirname(__DIR__);
    $projectRoot = rtrim($projectRoot, '/\\');
    $external = dirname($projectRoot) . DIRECTORY_SEPARATOR . 'retro-data';

    if (is_dir($external)) {
        return $external;
    }

    return $projectRoot . DIRECTORY_SEPARATOR . 'data';
}

function retroArchiveDatabase(?string $path = null): PDO
{
    $path ??= retroArchiveDataDir() . '/retro.sqlite';
    $directory = dirname($path);
    if (!is_dir($directory) && !mkdir($directory, 0770, true) && !is_dir($directory)) {
        throw new RuntimeException('Az archívum adatkönyvtára nem hozható létre.');
    }

    $db = new PDO('sqlite:' . $path, null, null, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
    $db->exec('PRAGMA foreign_keys = ON');
    $db->exec('PRAGMA busy_timeout = 5000');
    return $db;
}

function retroRequireFts5(PDO $db): void
{
    try {
        $db->exec('CREATE VIRTUAL TABLE temp.retro_fts5_probe USING fts5(body)');
        $db->exec('DROP TABLE temp.retro_fts5_probe');
    } catch (Throwable $error) {
        throw new RuntimeException('A szerveren az SQLite FTS5 nem érhető el.', 0, $error);
    }
}

function retroEnsureArchiveSchema(PDO $db): void
{
    retroRequireFts5($db);

    $db->exec(<<<'SQL'
CREATE TABLE IF NOT EXISTS archive_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_key TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    original_url TEXT NOT NULL,
    wayback_timestamp TEXT NOT NULL,
    archive_url TEXT NOT NULL,
    local_path TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    content_text TEXT NOT NULL DEFAULT '',
    indexed_at TEXT NOT NULL,
    UNIQUE(original_url, wayback_timestamp)
)
SQL);

    $db->exec(<<<'SQL'
CREATE VIRTUAL TABLE IF NOT EXISTS archive_pages_fts USING fts5(
    title,
    content_text,
    content='archive_pages',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
)
SQL);

    $db->exec(<<<'SQL'
CREATE TRIGGER IF NOT EXISTS archive_pages_ai AFTER INSERT ON archive_pages BEGIN
  INSERT INTO archive_pages_fts(rowid, title, content_text)
  VALUES (new.id, new.title, new.content_text);
END
SQL);

    $db->exec(<<<'SQL'
CREATE TRIGGER IF NOT EXISTS archive_pages_ad AFTER DELETE ON archive_pages BEGIN
  INSERT INTO archive_pages_fts(archive_pages_fts, rowid, title, content_text)
  VALUES ('delete', old.id, old.title, old.content_text);
END
SQL);

    $db->exec(<<<'SQL'
CREATE TRIGGER IF NOT EXISTS archive_pages_au AFTER UPDATE ON archive_pages BEGIN
  INSERT INTO archive_pages_fts(archive_pages_fts, rowid, title, content_text)
  VALUES ('delete', old.id, old.title, old.content_text);
  INSERT INTO archive_pages_fts(rowid, title, content_text)
  VALUES (new.id, new.title, new.content_text);
END
SQL);
}

function retroArchiveSnapshotKey(string $originalUrl, string $timestamp): string
{
    return hash('sha256', $originalUrl . "\n" . $timestamp);
}

/** @return array{title:string,text:string} */
function retroExtractArchivedPage(string $html): array
{
    if ($html === '') {
        return ['title' => '', 'text' => ''];
    }
    if (!class_exists('DOMDocument')) {
        throw new RuntimeException('A PHP DOM bővítmény nem érhető el.');
    }

    $previous = libxml_use_internal_errors(true);
    try {
        $document = new DOMDocument();
        $loaded = $document->loadHTML('<?xml encoding="UTF-8">' . $html, LIBXML_NOERROR | LIBXML_NOWARNING | LIBXML_NONET);
        if (!$loaded) {
            return ['title' => '', 'text' => ''];
        }

        $xpath = new DOMXPath($document);
        foreach (['script', 'style', 'noscript', 'template', 'svg'] as $tag) {
            $nodes = $xpath->query('//' . $tag);
            if ($nodes === false) {
                continue;
            }
            $toRemove = [];
            foreach ($nodes as $node) {
                $toRemove[] = $node;
            }
            foreach ($toRemove as $node) {
                $node->parentNode?->removeChild($node);
            }
        }

        $title = '';
        $titleNodes = $document->getElementsByTagName('title');
        if ($titleNodes->length > 0) {
            $title = retroNormalizeArchiveText((string) $titleNodes->item(0)?->textContent);
        }

        $body = $document->getElementsByTagName('body')->item(0);
        $text = retroNormalizeArchiveText((string) ($body?->textContent ?? $document->textContent));
        return ['title' => $title, 'text' => $text];
    } finally {
        libxml_clear_errors();
        libxml_use_internal_errors($previous);
    }
}

function retroNormalizeArchiveText(string $text): string
{
    $text = html_entity_decode($text, ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $text = preg_replace('/[\p{Z}\s]+/u', ' ', $text) ?? $text;
    return trim($text);
}

/** @return array<int,array{domain:string,limit:int}> */
function retroLoadSources(string $path): array
{
    if (!is_file($path)) {
        throw new RuntimeException('A forráskonfiguráció nem található.');
    }

    $raw = require $path;
    if (!is_array($raw)) {
        throw new RuntimeException('A forráskonfiguráció hibás.');
    }

    $normalized = [];
    $order = [];
    foreach ($raw as $entry) {
        if (is_string($entry)) {
            $entry = ['domain' => $entry];
        }
        if (!is_array($entry)) {
            continue;
        }

        $domain = trim((string) ($entry['domain'] ?? ''));
        if ($domain === '' || str_contains($domain, '://') || str_contains($domain, '/') || str_contains($domain, '?') || str_contains($domain, '#')) {
            continue;
        }

        $domain = rtrim(strtolower($domain), '.');
        if (function_exists('idn_to_ascii')) {
            $ascii = idn_to_ascii($domain, IDNA_DEFAULT, INTL_IDNA_VARIANT_UTS46);
            if (is_string($ascii) && $ascii !== '') {
                $domain = strtolower($ascii);
            }
        }
        if (!preg_match('/^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/', $domain)) {
            continue;
        }

        $limit = (int) ($entry['limit'] ?? 150);
        $limit = max(1, min(200, $limit));
        if (!array_key_exists($domain, $normalized)) {
            $order[] = $domain;
        }
        $normalized[$domain] = ['domain' => $domain, 'limit' => $limit];
    }

    $result = [];
    foreach ($order as $domain) {
        $result[] = $normalized[$domain];
    }
    return $result;
}

/** @param array<int,string> $arguments */
function retroIndexLimitOverride(array $arguments): ?int
{
    foreach (array_slice($arguments, 1) as $argument) {
        if (!str_starts_with($argument, '--limit=')) {
            continue;
        }
        $value = substr($argument, strlen('--limit='));
        if (!preg_match('/^\d+$/', $value)) {
            throw new InvalidArgumentException('A --limit értéke egész szám legyen.');
        }
        return max(1, min(200, (int) $value));
    }
    return null;
}

function retroArchivePath(string $baseDir, string $domain, string $timestamp, string $originalUrl): string
{
    $safeDomain = preg_replace('/[^a-z0-9.-]+/i', '_', strtolower($domain)) ?: 'unknown';
    $safeTimestamp = preg_replace('/[^0-9]/', '', $timestamp) ?: 'unknown';
    $hash = substr(hash('sha256', $originalUrl), 0, 16);
    return rtrim($baseDir, '/\\') . DIRECTORY_SEPARATOR . $safeDomain . DIRECTORY_SEPARATOR . $safeTimestamp . '-' . $hash . '.html';
}

function retroArchiveUrlIsIndexable(string $originalUrl): bool
{
    $path = parse_url($originalUrl, PHP_URL_PATH);
    if (!is_string($path)) {
        return false;
    }
    $decodedPath = rawurldecode($path);
    return preg_match('~(?:^|/)404(?:/|$)~', $decodedPath) !== 1;
}

function retroSnapshotExists(PDO $db, string $originalUrl, string $timestamp): bool
{
    $statement = $db->prepare('SELECT 1 FROM archive_pages WHERE original_url = :url AND wayback_timestamp = :timestamp LIMIT 1');
    $statement->execute(['url' => $originalUrl, 'timestamp' => $timestamp]);
    return $statement->fetchColumn() !== false;
}

function retroSnapshotId(PDO $db, string $originalUrl, string $timestamp): ?int
{
    $statement = $db->prepare('SELECT id FROM archive_pages WHERE original_url = :url AND wayback_timestamp = :timestamp LIMIT 1');
    $statement->execute(['url' => $originalUrl, 'timestamp' => $timestamp]);
    $value = $statement->fetchColumn();
    return $value === false ? null : (int) $value;
}

/** @param array{domain:string,original:string,timestamp:string,archiveUrl:string} $metadata */
function retroStoreSnapshot(PDO $db, array $metadata, string $html, string $archiveBaseDir): int
{
    $domain = strtolower(trim((string) ($metadata['domain'] ?? '')));
    $original = trim((string) ($metadata['original'] ?? ''));
    $timestamp = trim((string) ($metadata['timestamp'] ?? ''));
    $archiveUrl = trim((string) ($metadata['archiveUrl'] ?? ''));
    if ($domain === '' || $original === '' || !preg_match('/^\d{14}$/', $timestamp) || $archiveUrl === '') {
        throw new InvalidArgumentException('Hiányos snapshot metaadat.');
    }

    $existing = retroSnapshotId($db, $original, $timestamp);
    if ($existing !== null) {
        return $existing;
    }

    $page = retroExtractArchivedPage($html);
    $path = retroArchivePath($archiveBaseDir, $domain, $timestamp, $original);
    $directory = dirname($path);
    if (!is_dir($directory) && !mkdir($directory, 0770, true) && !is_dir($directory)) {
        throw new RuntimeException('A snapshot könyvtár nem hozható létre.');
    }
    if (file_put_contents($path, $html, LOCK_EX) === false) {
        throw new RuntimeException('A snapshot nem menthető helyben.');
    }
    @chmod($path, 0640);

    try {
        $db->beginTransaction();
        $statement = $db->prepare(<<<'SQL'
INSERT INTO archive_pages
(snapshot_key, domain, original_url, wayback_timestamp, archive_url, local_path, title, content_text, indexed_at)
VALUES (:snapshot_key, :domain, :original_url, :wayback_timestamp, :archive_url, :local_path, :title, :content_text, :indexed_at)
SQL);
        $statement->execute([
            'snapshot_key' => retroArchiveSnapshotKey($original, $timestamp),
            'domain' => $domain,
            'original_url' => $original,
            'wayback_timestamp' => $timestamp,
            'archive_url' => $archiveUrl,
            'local_path' => $path,
            'title' => $page['title'],
            'content_text' => $page['text'],
            'indexed_at' => gmdate('c'),
        ]);
        $id = (int) $db->lastInsertId();
        $db->commit();
        return $id;
    } catch (PDOException $error) {
        if ($db->inTransaction()) {
            $db->rollBack();
        }
        $existing = retroSnapshotId($db, $original, $timestamp);
        if ($existing !== null) {
            return $existing;
        }
        @unlink($path);
        throw $error;
    } catch (Throwable $error) {
        if ($db->inTransaction()) {
            $db->rollBack();
        }
        @unlink($path);
        throw $error;
    }
}

/**
 * Stores a snapshot pushed by the crawler's periodic sync job, skipping the
 * local HTML capture step used by the browser-triggered indexer.
 *
 * @param array{domain:string,original_url:string,wayback_timestamp:string,archive_url:string,title?:string,content_text?:string} $record
 * @return bool true when a new row was inserted, false when it already existed
 */
function retroIngestSnapshot(PDO $db, array $record): bool
{
    $domain = strtolower(trim((string) ($record['domain'] ?? '')));
    $original = trim((string) ($record['original_url'] ?? ''));
    $timestamp = trim((string) ($record['wayback_timestamp'] ?? ''));
    $archiveUrl = trim((string) ($record['archive_url'] ?? ''));
    $title = retroNormalizeArchiveText((string) ($record['title'] ?? ''));
    $contentText = retroNormalizeArchiveText((string) ($record['content_text'] ?? ''));

    if ($domain === '' || $original === '' || !preg_match('/^\d{14}$/', $timestamp) || $archiveUrl === '') {
        throw new InvalidArgumentException('Hiányos ingest metaadat.');
    }

    $statement = $db->prepare(<<<'SQL'
INSERT OR IGNORE INTO archive_pages
(snapshot_key, domain, original_url, wayback_timestamp, archive_url, local_path, title, content_text, indexed_at)
VALUES (:snapshot_key, :domain, :original_url, :wayback_timestamp, :archive_url, '', :title, :content_text, :indexed_at)
SQL);
    $statement->execute([
        'snapshot_key' => retroArchiveSnapshotKey($original, $timestamp),
        'domain' => $domain,
        'original_url' => $original,
        'wayback_timestamp' => $timestamp,
        'archive_url' => $archiveUrl,
        'title' => $title,
        'content_text' => $contentText,
        'indexed_at' => gmdate('c'),
    ]);

    return $statement->rowCount() > 0;
}

function retroBuildCdxUrl(string $domain, int $limit): string
{
    $limit = max(1, min(200, $limit));
    $query = http_build_query([
        'url' => $domain . '/*',
        'output' => 'json',
        'fl' => 'timestamp,original,statuscode,mimetype,digest,length',
        'collapse' => 'urlkey',
        'limit' => (string) $limit,
    ]);
    return 'https://web.archive.org/cdx/search/cdx?' . $query
        . '&filter=statuscode%3A200&filter=mimetype%3Atext%2Fhtml';
}

function retroWaybackUrl(string $timestamp, string $originalUrl, bool $raw = false): string
{
    return 'https://web.archive.org/web/' . rawurlencode($timestamp) . ($raw ? 'id_/' : '/') . $originalUrl;
}

/** @return array{ok:bool,status:int,body:string,error:string,errno:int} */
function retroHttpGet(string $url, int $connectTimeout = 3, int $timeout = 15): array
{
    $curl = curl_init($url);
    if ($curl === false) {
        return ['ok' => false, 'status' => 0, 'body' => '', 'error' => 'cURL init failed', 'errno' => -1];
    }
    curl_setopt_array($curl, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_CONNECTTIMEOUT => max(1, $connectTimeout),
        CURLOPT_TIMEOUT => max(1, $timeout),
        CURLOPT_USERAGENT => 'retro-kereso-indexer/1.0',
        CURLOPT_HTTPHEADER => ['Accept: text/html,application/json;q=0.9,*/*;q=0.1'],
    ]);
    $body = curl_exec($curl);
    $status = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
    $errno = curl_errno($curl);
    $error = curl_error($curl);
    curl_close($curl);

    $ok = is_string($body) && $status >= 200 && $status < 300;
    return [
        'ok' => $ok,
        'status' => $status,
        'body' => is_string($body) ? $body : '',
        'error' => $error,
        'errno' => $errno,
    ];
}

function retroFtsQuery(string $query): string
{
    preg_match_all('/[\p{L}\p{N}]+/u', $query, $matches);
    $terms = $matches[0] ?? [];
    $terms = array_values(array_filter($terms, static fn(string $term): bool => $term !== ''));
    if ($terms === []) {
        return '';
    }
    return implode(' AND ', array_map(
        static fn(string $term): string => '"' . str_replace('"', '""', $term) . '"*',
        $terms
    ));
}

/** @return array<int,array{title:string,original:string,domain:string,timestamp:string,snippet:string,archiveUrl:string}> */
function retroSearchArchive(PDO $db, string $query, int $limit = 20): array
{
    $ftsQuery = retroFtsQuery(trim($query));
    if ($ftsQuery === '') {
        return [];
    }
    $limit = max(1, min(50, $limit));

    $sql = <<<SQL
SELECT
  COALESCE(NULLIF(p.title, ''), p.original_url) AS title,
  p.original_url AS original,
  p.domain AS domain,
  p.wayback_timestamp AS timestamp,
  snippet(archive_pages_fts, 1, '', '', ' … ', 28) AS snippet,
  p.archive_url AS archiveUrl
FROM archive_pages_fts
JOIN archive_pages p ON p.id = archive_pages_fts.rowid
WHERE archive_pages_fts MATCH :query
ORDER BY bm25(archive_pages_fts), p.wayback_timestamp DESC
LIMIT {$limit}
SQL;
    $statement = $db->prepare($sql);
    $statement->execute(['query' => $ftsQuery]);
    return $statement->fetchAll();
}
