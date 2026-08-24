<?php

declare(strict_types=1);

$api = file_get_contents(__DIR__ . '/../api.php');

function requireWaybackQuery(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

requireWaybackQuery(strpos($api, "'filter' => ['statuscode:200', 'mimetype:text/html']") === false, 'Wayback filters must not be encoded as a PHP array');
requireWaybackQuery(strpos($api, "filter=statuscode%3A200") !== false, 'statuscode filter must be sent as repeated filter parameter');
requireWaybackQuery(strpos($api, "filter=mimetype%3Atext%2Fhtml") !== false, 'mimetype filter must be sent as repeated filter parameter');

fwrite(STDOUT, "PASS\n");
