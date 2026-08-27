<?php

declare(strict_types=1);

require_once __DIR__ . '/auth.php';
require_once __DIR__ . '/lib/archive.php';
require_once __DIR__ . '/lib/logger.php';
retroStartSession();

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
// Expose only the generated correlation id; internal log details remain server-side.
header('X-Request-ID: ' . retroRequestId());

function respond(int $status, array $data): never
{
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function requestBody(): array
{
    $body = json_decode(file_get_contents('php://input'), true);
    return is_array($body) ? $body : [];
}

$action = $_GET['action'] ?? '';

if ($action === 'session') {
    respond(200, ['authenticated' => retroIsAuthenticated()]);
}

if ($action === 'login' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $body = requestBody();
    try {
        $passwordHash = retroPasswordHash();
    } catch (RuntimeException $error) {
        retroLog('error', 'authentication_not_configured', retroExceptionContext($error, [
            'action' => 'login',
        ]));
        respond(500, ['error' => 'A hozzáférés nincs konfigurálva.']);
    }

    if (!retroVerifyPassword((string) ($body['password'] ?? ''), $passwordHash)) {
        // Never include the submitted password or request body in authentication logs.
        retroLog('warning', 'login_failed', [
            'action' => 'login',
        ]);
        usleep(250000);
        respond(401, ['error' => 'Hibás jelszó.']);
    }

    session_regenerate_id(true);
    $_SESSION['retro_authenticated'] = true;
    retroLog('info', 'login_succeeded', [
        'action' => 'login',
    ]);
    respond(200, ['ok' => true]);
}

if ($action === 'logout' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $_SESSION = [];
    if (ini_get('session.use_cookies')) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000, $params['path'], $params['domain'], $params['secure'], $params['httponly']);
    }
    session_destroy();
    retroLog('info', 'logout_succeeded', [
        'action' => 'logout',
    ]);
    respond(200, ['ok' => true]);
}

if ($action === 'ingest' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        $expectedToken = retroIngestToken();
    } catch (RuntimeException $error) {
        retroLog('error', 'ingest_not_configured', retroExceptionContext($error, [
            'action' => 'ingest',
        ]));
        respond(500, ['error' => 'A feltöltés nincs konfigurálva.']);
    }

    $providedToken = (string) ($_SERVER['HTTP_X_INGEST_TOKEN'] ?? '');
    if ($providedToken === '' || !hash_equals($expectedToken, $providedToken)) {
        retroLog('warning', 'ingest_unauthorized', ['action' => 'ingest']);
        respond(401, ['error' => 'Érvénytelen ingest token.']);
    }

    $body = requestBody();
    $records = is_array($body['records'] ?? null) ? $body['records'] : [];

    try {
        $database = retroArchiveDatabase();
        retroEnsureArchiveSchema($database);
    } catch (Throwable $error) {
        retroLog('error', 'ingest_db_unavailable', retroExceptionContext($error, ['action' => 'ingest']));
        respond(500, ['error' => 'A helyi archívum nem érhető el.']);
    }

    $inserted = 0;
    $skipped = 0;
    foreach ($records as $record) {
        if (!is_array($record)) {
            $skipped++;
            continue;
        }
        try {
            if (retroIngestSnapshot($database, $record)) {
                $inserted++;
            } else {
                $skipped++;
            }
        } catch (Throwable $error) {
            $skipped++;
            retroLog('warning', 'ingest_record_failed', retroExceptionContext($error, ['action' => 'ingest']));
        }
    }

    retroLog('info', 'ingest_completed', [
        'action' => 'ingest',
        'inserted' => $inserted,
        'skipped' => $skipped,
        'total' => count($records),
    ]);
    respond(200, ['inserted' => $inserted, 'skipped' => $skipped, 'total' => count($records)]);
}

if ($action !== 'search') {
    retroLog('warning', 'unknown_api_action', [
        'action' => (string) $action,
        'method' => (string) ($_SERVER['REQUEST_METHOD'] ?? ''),
    ]);
    respond(404, ['error' => 'Ismeretlen művelet.']);
}

if (!retroIsAuthenticated()) {
    retroLog('warning', 'unauthenticated_search', [
        'action' => 'search',
    ]);
    respond(401, ['error' => 'A kereséshez bejelentkezés szükséges.']);
}

$query = trim((string) ($_GET['q'] ?? ''));
$queryLength = function_exists('mb_strlen') ? mb_strlen($query, 'UTF-8') : strlen($query);
if ($query === '' || $queryLength > 200) {
    // Log only the length, not the search phrase itself, to minimize retention of user-entered text.
    retroLog('warning', 'invalid_search_query', [
        'query_length' => $queryLength,
    ]);
    respond(400, ['error' => 'Adj meg egy 1–200 karakteres keresőkifejezést.']);
}

try {
    $database = retroArchiveDatabase();
    retroEnsureArchiveSchema($database);
    $items = retroSearchArchive($database, $query, 20);
} catch (RuntimeException $error) {
    retroLog('error', 'archive_search_failed', retroExceptionContext($error, [
        'query_length' => $queryLength,
        'error_type' => 'runtime',
    ]));
    respond(500, ['error' => 'A helyi archívum keresése nem sikerült.']);
} catch (Throwable $error) {
    retroLog('error', 'archive_search_failed', retroExceptionContext($error, [
        'query_length' => $queryLength,
        'error_type' => 'unexpected',
    ]));
    respond(500, ['error' => 'A helyi archívum keresése nem sikerült.']);
}

respond(200, ['query' => $query, 'results' => $items]);
