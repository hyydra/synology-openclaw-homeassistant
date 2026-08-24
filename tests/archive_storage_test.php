<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/archive.php';

$root = sys_get_temp_dir() . '/retro-storage-' . bin2hex(random_bytes(4));
$db = retroArchiveDatabase($root . '/retro.sqlite');
retroEnsureArchiveSchema($db);

$meta = [
    'domain' => 'pecs.hu',
    'original' => 'https://pecs.hu/regi-oldal',
    'timestamp' => '20040203040506',
    'archiveUrl' => 'https://web.archive.org/web/20040203040506id_/https://pecs.hu/regi-oldal',
];
$html = '<html><head><title>Pécsi oldal</title></head><body>Széchenyi tér Pécs belvárosában.</body></html>';

$id = retroStoreSnapshot($db, $meta, $html, $root . '/archive');
if ($id <= 0) {
    fwrite(STDERR, "FAIL: first snapshot not stored\n");
    exit(1);
}
if (!retroSnapshotExists($db, $meta['original'], $meta['timestamp'])) {
    fwrite(STDERR, "FAIL: snapshot lookup failed\n");
    exit(1);
}
$row = $db->query('SELECT * FROM archive_pages LIMIT 1')->fetch();
if (!is_array($row) || !is_file($row['local_path'])) {
    fwrite(STDERR, "FAIL: raw html file missing\n");
    exit(1);
}
if (pathinfo($row['local_path'], PATHINFO_EXTENSION) !== 'html') {
    fwrite(STDERR, "FAIL: archive extension must be html\n");
    exit(1);
}
$count = (int) $db->query("SELECT count(*) FROM archive_pages_fts WHERE archive_pages_fts MATCH 'pécs'")->fetchColumn();
if ($count !== 1) {
    fwrite(STDERR, "FAIL: stored snapshot not indexed\n");
    exit(1);
}
$second = retroStoreSnapshot($db, $meta, $html, $root . '/archive');
if ($second !== $id || (int) $db->query('SELECT count(*) FROM archive_pages')->fetchColumn() !== 1) {
    fwrite(STDERR, "FAIL: duplicate snapshot was not skipped\n");
    exit(1);
}

fwrite(STDOUT, "PASS\n");
