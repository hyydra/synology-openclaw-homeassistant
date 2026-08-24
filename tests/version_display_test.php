<?php

declare(strict_types=1);

$root = dirname(__DIR__);
$versionPath = $root . '/VERSION';
$indexPath = $root . '/index.php';

if (!is_file($versionPath)) {
    fwrite(STDERR, "FAIL: VERSION file missing\n");
    exit(1);
}

$version = trim((string) file_get_contents($versionPath));
if (!preg_match('/^\d+\.\d+\.\d+$/', $version)) {
    fwrite(STDERR, "FAIL: VERSION must use semantic version format\n");
    exit(1);
}

$index = file_get_contents($indexPath);
if (!is_string($index)) {
    fwrite(STDERR, "FAIL: index.php missing\n");
    exit(1);
}

foreach (["/VERSION", 'build-version', 'htmlspecialchars($buildVersion'] as $needle) {
    if (!str_contains($index, $needle)) {
        fwrite(STDERR, "FAIL: version display missing {$needle}\n");
        exit(1);
    }
}

fwrite(STDOUT, "PASS\n");
