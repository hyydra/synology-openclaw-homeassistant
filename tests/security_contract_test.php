<?php

declare(strict_types=1);

$api = file_get_contents(__DIR__ . '/../api.php');
$app = file_get_contents(__DIR__ . '/../app.js');
$indexPath = __DIR__ . '/../index.php';

function requireCondition(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

requireCondition(strpos($api, "require_once __DIR__ . '/auth.php'") !== false, 'api.php must use shared auth helper');
requireCondition(strpos($api, 'ACCESS_PASSWORD') === false, 'api.php must not contain a hard-coded password');
requireCondition(strpos($api, "action === 'logout'") !== false, 'api.php must expose logout');
requireCondition(is_file($indexPath), 'index.php must gate the application server-side');
requireCondition(strpos($app, 'action=logout') !== false, 'frontend must support logout');
requireCondition(strpos($app, 'innerHTML') === false, 'frontend must not render archive data through innerHTML');

fwrite(STDOUT, "PASS\n");
