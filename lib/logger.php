<?php

declare(strict_types=1);

require_once __DIR__ . '/archive.php';

/**
 * Returns a stable request identifier for correlating browser, API, and server log events.
 * A fresh server-generated value is used instead of trusting a client-supplied header.
 */
function retroRequestId(): string
{
    static $requestId = null;
    if (is_string($requestId) && $requestId !== '') {
        return $requestId;
    }

    try {
        $requestId = bin2hex(random_bytes(8));
    } catch (Throwable) {
        $requestId = str_replace('.', '', uniqid('retro', true));
    }

    return $requestId;
}

/**
 * Returns the default log file outside the public webroot whenever the external data directory exists.
 */
function retroLogPath(?string $projectRoot = null): string
{
    return retroArchiveDataDir($projectRoot) . DIRECTORY_SEPARATOR . 'logs' . DIRECTORY_SEPARATOR . 'retro.log';
}

/**
 * Recursively removes secrets and bounds user-controlled strings before they reach persistent logs.
 * Logging must remain useful for diagnostics without becoming a secondary credential store.
 */
function retroLogSanitize(mixed $value, ?string $key = null): mixed
{
    $normalizedKey = strtolower((string) $key);
    $sensitiveFragments = [
        'password',
        'passwd',
        'authorization',
        'cookie',
        'token',
        'secret',
        'session',
        'password_hash',
        'api_key',
        'apikey',
    ];

    foreach ($sensitiveFragments as $fragment) {
        if ($normalizedKey !== '' && str_contains($normalizedKey, $fragment)) {
            return '[REDACTED]';
        }
    }

    if (is_array($value)) {
        $result = [];
        foreach ($value as $childKey => $childValue) {
            $result[$childKey] = retroLogSanitize($childValue, (string) $childKey);
        }
        return $result;
    }

    if (is_object($value)) {
        return '[OBJECT:' . $value::class . ']';
    }

    if (is_resource($value)) {
        return '[RESOURCE]';
    }

    if (is_string($value)) {
        // Keep individual fields small so malformed upstream responses cannot grow the log without bounds.
        $limit = 2000;
        if (strlen($value) > $limit) {
            return substr($value, 0, $limit) . '...[truncated]';
        }
        return $value;
    }

    return $value;
}

/**
 * Appends one structured JSON line to the application log.
 * Logging failures are deliberately non-fatal so diagnostics can never take the search service down.
 */
function retroLog(string $level, string $event, array $context = [], ?string $path = null): bool
{
    $path ??= retroLogPath();
    $directory = dirname($path);

    if (!is_dir($directory) && !@mkdir($directory, 0770, true) && !is_dir($directory)) {
        return false;
    }

    $entry = [
        'timestamp' => gmdate('c'),
        'level' => strtoupper(trim($level) !== '' ? trim($level) : 'INFO'),
        'request_id' => retroRequestId(),
        'event' => $event,
        'context' => retroLogSanitize($context),
    ];

    $json = json_encode($entry, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if (!is_string($json)) {
        return false;
    }

    $written = @file_put_contents($path, $json . PHP_EOL, FILE_APPEND | LOCK_EX);
    if ($written === false) {
        return false;
    }

    // Restrict newly created logs where the hosting filesystem supports POSIX permissions.
    @chmod($path, 0640);
    return true;
}

/**
 * Builds a diagnostic exception context for server-side logs only.
 * This must never be returned directly to a browser response.
 */
function retroExceptionContext(Throwable $error, array $extra = []): array
{
    return array_merge($extra, [
        'exception' => $error::class,
        'message' => $error->getMessage(),
        'code' => $error->getCode(),
        'file' => $error->getFile(),
        'line' => $error->getLine(),
    ]);
}
