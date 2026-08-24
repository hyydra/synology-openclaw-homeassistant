<?php

declare(strict_types=1);

require_once __DIR__ . '/auth.php';
require_once __DIR__ . '/lib/archive.php';
retroStartSession();

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

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
    } catch (RuntimeException) {
        respond(500, ['error' => 'A hozzáférés nincs konfigurálva.']);
    }

    if (!retroVerifyPassword((string) ($body['password'] ?? ''), $passwordHash)) {
        usleep(250000);
        respond(401, ['error' => 'Hibás jelszó.']);
    }

    session_regenerate_id(true);
    $_SESSION['retro_authenticated'] = true;
    respond(200, ['ok' => true]);
}

if ($action === 'logout' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $_SESSION = [];
    if (ini_get('session.use_cookies')) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000, $params['path'], $params['domain'], $params['secure'], $params['httponly']);
    }
    session_destroy();
    respond(200, ['ok' => true]);
}

if ($action !== 'search') {
    respond(404, ['error' => 'Ismeretlen művelet.']);
}

if (!retroIsAuthenticated()) {
    respond(401, ['error' => 'A kereséshez bejelentkezés szükséges.']);
}

$query = trim((string) ($_GET['q'] ?? ''));
$queryLength = function_exists('mb_strlen') ? mb_strlen($query, 'UTF-8') : strlen($query);
if ($query === '' || $queryLength > 200) {
    respond(400, ['error' => 'Adj meg egy 1–200 karakteres keresőkifejezést.']);
}

try {
    $database = retroArchiveDatabase();
    retroEnsureArchiveSchema($database);
    $items = retroSearchArchive($database, $query, 20);
} catch (RuntimeException $error) {
    respond(500, ['error' => $error->getMessage()]);
} catch (Throwable) {
    respond(500, ['error' => 'A helyi archívum keresése nem sikerült.']);
}

respond(200, ['query' => $query, 'results' => $items]);
