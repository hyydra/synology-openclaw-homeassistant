<?php

declare(strict_types=1);

$api = file_get_contents(__DIR__ . '/../api.php');

function requireFastWayback(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

requireFastWayback(strpos($api, "'limit' => '20'") !== false, 'Wayback result limit must be 20');
requireFastWayback(strpos($api, 'CURLOPT_CONNECTTIMEOUT => 3') !== false, 'Wayback connect timeout must be 3 seconds');
requireFastWayback(strpos($api, 'CURLOPT_TIMEOUT => 8') !== false, 'Wayback total timeout must be 8 seconds');
requireFastWayback(strpos($api, 'CURLE_OPERATION_TIMEDOUT') !== false, 'Wayback timeout must have a dedicated error response');

fwrite(STDOUT, "PASS\n");
