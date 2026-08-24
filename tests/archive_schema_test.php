<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/archive.php';

function failArchiveSchema(string $message): never
{
    fwrite(STDERR, "FAIL: {$message}\n");
    exit(1);
}

$path = sys_get_temp_dir() . '/retro-archive-schema-' . bin2hex(random_bytes(4)) . '.sqlite';
$db = retroArchiveDatabase($path);
retroRequireFts5($db);
retroEnsureArchiveSchema($db);

$tables = $db->query("SELECT name FROM sqlite_master WHERE type IN ('table','view')")->fetchAll(PDO::FETCH_COLUMN);
if (!in_array('archive_pages', $tables, true)) {
    failArchiveSchema('archive_pages table missing');
}
if (!in_array('archive_pages_fts', $tables, true)) {
    failArchiveSchema('archive_pages_fts table missing');
}

$insert = $db->prepare('INSERT INTO archive_pages (snapshot_key, domain, original_url, wayback_timestamp, archive_url, local_path, title, content_text, indexed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)');
$args = [
    retroArchiveSnapshotKey('https://pecs.hu/a', '20010101000000'),
    'pecs.hu',
    'https://pecs.hu/a',
    '20010101000000',
    'https://web.archive.org/web/20010101000000id_/https://pecs.hu/a',
    '/tmp/a.html',
    'Pécs városa',
    'Régi pécsi oldal szövege',
    gmdate('c'),
];
$insert->execute($args);

try {
    $insert->execute($args);
    failArchiveSchema('duplicate URL+timestamp was accepted');
} catch (PDOException) {
    // Expected unique violation.
}

$count = (int) $db->query("SELECT count(*) FROM archive_pages_fts WHERE archive_pages_fts MATCH 'pécs'")->fetchColumn();
if ($count !== 1) {
    failArchiveSchema('FTS trigger/index did not contain inserted page');
}

@unlink($path);
fwrite(STDOUT, "PASS\n");
