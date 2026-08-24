<?php

declare(strict_types=1);

require_once dirname(__DIR__) . '/lib/archive.php';

$url = retroBuildCdxUrl('pecs.hu', 100);
$query = parse_url($url, PHP_URL_QUERY);
if (!is_string($query)) {
    fwrite(STDERR, "FAIL: CDX query missing\n");
    exit(1);
}

parse_str($query, $params);

if (($params['collapse'] ?? null) !== 'urlkey') {
    fwrite(STDERR, 'FAIL: expected collapse=urlkey, got ' . ($params['collapse'] ?? 'missing') . "\n");
    exit(1);
}

if (str_contains($url, 'timestamp%3A6') || str_contains($url, 'timestamp:6')) {
    fwrite(STDERR, "FAIL: monthly timestamp collapse still present\n");
    exit(1);
}

fwrite(STDOUT, "PASS\n");
