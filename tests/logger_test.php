<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/archive.php';
require_once __DIR__ . '/../lib/logger.php';

function loggerAssert(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

$base = sys_get_temp_dir() . '/retro-logger-' . bin2hex(random_bytes(4));
$logPath = $base . '/logs/retro.log';

// Sensitive values must never be persisted even when deeply nested.
$context = [
    'action' => 'login',
    'password' => 'super-secret-password',
    'nested' => [
        'authorization' => 'Bearer secret-token',
        'session_id' => 'session-secret',
        'safe_value' => 'kept',
    ],
];

loggerAssert(retroLog('warning', 'test_event', $context, $logPath), 'logger should write successfully');
loggerAssert(is_file($logPath), 'logger should create the log file');

$raw = file_get_contents($logPath);
loggerAssert(is_string($raw) && $raw !== '', 'log file should contain one JSON line');
loggerAssert(!str_contains($raw, 'super-secret-password'), 'password must be redacted');
loggerAssert(!str_contains($raw, 'Bearer secret-token'), 'authorization data must be redacted');
loggerAssert(!str_contains($raw, 'session-secret'), 'session data must be redacted');
loggerAssert(str_contains($raw, '"safe_value":"kept"'), 'non-sensitive context should remain');

$entry = json_decode(trim($raw), true);
loggerAssert(is_array($entry), 'log entry should be valid JSON');
loggerAssert(($entry['level'] ?? null) === 'WARNING', 'log level should be normalized');
loggerAssert(($entry['event'] ?? null) === 'test_event', 'event name should be recorded');
loggerAssert(is_string($entry['request_id'] ?? null) && strlen($entry['request_id']) >= 8, 'request id should be present');
loggerAssert(is_string($entry['timestamp'] ?? null) && $entry['timestamp'] !== '', 'timestamp should be present');

// Oversized strings are truncated so one bad payload cannot explode the log file.
$sanitized = retroLogSanitize(['payload' => str_repeat('x', 5000)]);
loggerAssert(strlen((string) ($sanitized['payload'] ?? '')) <= 2100, 'long strings should be bounded');

@unlink($logPath);
@rmdir(dirname($logPath));
@rmdir($base);

fwrite(STDOUT, "PASS\n");
