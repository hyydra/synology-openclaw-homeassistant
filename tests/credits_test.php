<?php

declare(strict_types=1);

$root = dirname(__DIR__);
$index = file_get_contents($root . '/index.php');
$readme = file_get_contents($root . '/README.md');

if (!is_string($index) || !is_string($readme)) {
    fwrite(STDERR, "FAIL: required files missing\n");
    exit(1);
}

$requiredIndex = [
    'Credits',
    'jsvine/waybackpack',
    'hartator/wayback-machine-downloader',
];

foreach ($requiredIndex as $needle) {
    if (!str_contains($index, $needle)) {
        fwrite(STDERR, "FAIL: index credit missing {$needle}\n");
        exit(1);
    }
}

$requiredReadme = [
    '## Credits',
    'jsvine/waybackpack',
    'hartator/wayback-machine-downloader',
    'informed by',
];

foreach ($requiredReadme as $needle) {
    if (!str_contains($readme, $needle)) {
        fwrite(STDERR, "FAIL: README credit missing {$needle}\n");
        exit(1);
    }
}

fwrite(STDOUT, "PASS\n");
