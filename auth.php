<?php

declare(strict_types=1);

function retroPasswordHash(): string
{
    $environmentHash = getenv('RETRO_PASSWORD_HASH');
    if (is_string($environmentHash) && $environmentHash !== '') {
        return $environmentHash;
    }

    $configPath = dirname(__DIR__) . '/retro-config.php';
    if (is_file($configPath)) {
        $config = require $configPath;
        $configHash = is_array($config) ? ($config['password_hash'] ?? null) : null;
        if (is_string($configHash) && $configHash !== '') {
            return $configHash;
        }
    }

    throw new RuntimeException('RETRO_PASSWORD_HASH nincs beállítva.');
}

function retroVerifyPassword(string $password, string $hash): bool
{
    return password_verify($password, $hash);
}

/**
 * Shared secret required on the archive ingest endpoint, so only the crawler's
 * sync script (never a browser) can write new snapshots into the archive.
 */
function retroIngestToken(): string
{
    $environmentToken = getenv('RETRO_INGEST_TOKEN');
    if (is_string($environmentToken) && $environmentToken !== '') {
        return $environmentToken;
    }

    $configPath = dirname(__DIR__) . '/retro-config.php';
    if (is_file($configPath)) {
        $config = require $configPath;
        $configToken = is_array($config) ? ($config['ingest_token'] ?? null) : null;
        if (is_string($configToken) && $configToken !== '') {
            return $configToken;
        }
    }

    throw new RuntimeException('RETRO_INGEST_TOKEN nincs beállítva.');
}

function retroStartSession(): void
{
    if (session_status() === PHP_SESSION_ACTIVE) {
        return;
    }

    $isHttps = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
        || (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https');

    session_name('retro_session');
    session_set_cookie_params([
        'lifetime' => 0,
        'path' => '/',
        'secure' => $isHttps,
        'httponly' => true,
        'samesite' => 'Strict',
    ]);
    session_start();
}

function retroIsAuthenticated(): bool
{
    return !empty($_SESSION['retro_authenticated']);
}

function retroRequireAuthentication(): void
{
    if (!retroIsAuthenticated()) {
        http_response_code(401);
        header('Content-Type: application/json; charset=utf-8');
        header('Cache-Control: no-store');
        echo json_encode(['error' => 'A művelethez bejelentkezés szükséges.'], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        exit;
    }
}
