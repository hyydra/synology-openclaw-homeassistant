<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/archive.php';

$root = sys_get_temp_dir() . '/retro-search-' . bin2hex(random_bytes(4));
$db = retroArchiveDatabase($root . '/retro.sqlite');
retroEnsureArchiveSchema($db);

retroStoreSnapshot($db, [
    'domain' => 'pecs.hu',
    'original' => 'https://pecs.hu/zsolnay',
    'timestamp' => '20050101000000',
    'archiveUrl' => 'https://web.archive.org/web/20050101000000id_/https://pecs.hu/zsolnay',
], '<html><head><title>Zsolnay negyed</title></head><body>A pécsi Zsolnay kulturális negyed története.</body></html>', $root . '/archive');

retroStoreSnapshot($db, [
    'domain' => 'pte.hu',
    'original' => 'https://pte.hu/egyetem',
    'timestamp' => '20060101000000',
    'archiveUrl' => 'https://web.archive.org/web/20060101000000id_/https://pte.hu/egyetem',
], '<html><head><title>Egyetem</title></head><body>Felsőoktatási hírek és kutatás.</body></html>', $root . '/archive');

$results = retroSearchArchive($db, 'pécs', 20);
if (count($results) !== 1) {
    fwrite(STDERR, "FAIL: keyword should match one page\n");
    exit(1);
}
$item = $results[0];
foreach (['title', 'original', 'domain', 'timestamp', 'snippet', 'archiveUrl'] as $field) {
    if (!array_key_exists($field, $item)) {
        fwrite(STDERR, "FAIL: missing result field {$field}\n");
        exit(1);
    }
}
if (!str_contains(mb_strtolower($item['snippet'], 'UTF-8'), 'pécs')) {
    fwrite(STDERR, "FAIL: snippet does not contain useful match context\n");
    exit(1);
}
if (count(retroSearchArchive($db, 'kutatás', 1)) > 1) {
    fwrite(STDERR, "FAIL: hard result limit ignored\n");
    exit(1);
}

fwrite(STDOUT, "PASS\n");
