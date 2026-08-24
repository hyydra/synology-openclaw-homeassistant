<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/archive.php';

$base = sys_get_temp_dir() . '/retro-data-dir-' . bin2hex(random_bytes(6));
$domainRoot = $base . DIRECTORY_SEPARATOR . 'example.test';
$projectRoot = $domainRoot . DIRECTORY_SEPARATOR . 'public_html';
$legacy = $projectRoot . DIRECTORY_SEPARATOR . 'data';
$external = $domainRoot . DIRECTORY_SEPARATOR . 'retro-data';

if (!mkdir($legacy, 0770, true) && !is_dir($legacy)) {
    fwrite(STDERR, "FAIL: temp legacy dir\n");
    exit(1);
}

try {
    if (!function_exists('retroArchiveDataDir')) {
        fwrite(STDERR, "FAIL: retroArchiveDataDir missing\n");
        exit(1);
    }

    $before = retroArchiveDataDir($projectRoot);
    if ($before !== $legacy) {
        fwrite(STDERR, "FAIL: legacy data dir should remain active before migration\n");
        exit(1);
    }

    if (!mkdir($external, 0770, true) && !is_dir($external)) {
        fwrite(STDERR, "FAIL: temp external dir\n");
        exit(1);
    }

    $after = retroArchiveDataDir($projectRoot);
    if ($after !== $external) {
        fwrite(STDERR, "FAIL: external retro-data dir should take precedence after migration\n");
        exit(1);
    }

    fwrite(STDOUT, "PASS\n");
} finally {
    @rmdir($external);
    @rmdir($legacy);
    @rmdir($projectRoot);
    @rmdir($domainRoot);
    @rmdir($base);
}
