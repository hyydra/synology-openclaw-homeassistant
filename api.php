<?php

declare(strict_types=1);

require_once __DIR__ . '/auth.php';
retroStartSession();

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

const DATABASE_PATH = __DIR__ . '/data/retro.sqlite';

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

function database(): PDO
{
    static $database;
    if ($database instanceof PDO) {
        return $database;
    }

    if (!is_dir(dirname(DATABASE_PATH)) && !mkdir(dirname(DATABASE_PATH), 0770, true) && !is_dir(dirname(DATABASE_PATH))) {
        throw new RuntimeException('Az adatkönyvtár nem hozható létre.');
    }

    $database = new PDO('sqlite:' . DATABASE_PATH, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
    $database->exec('PRAGMA foreign_keys = ON');
    $database->exec('CREATE TABLE IF NOT EXISTS searches (id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT NOT NULL, searched_at TEXT NOT NULL)');
    $database->exec('CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY AUTOINCREMENT, search_id INTEGER NOT NULL, timestamp TEXT, original TEXT, status TEXT, mimetype TEXT, digest TEXT, length TEXT, archive_url TEXT NOT NULL, FOREIGN KEY(search_id) REFERENCES searches(id))');
    return $database;
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

$target = trim((string) ($_GET['url'] ?? ''));
if ($target === '' || strlen($target) > 500 || !preg_match('/^https?:\/\//i', $target)) {
    respond(400, ['error' => 'Adj meg egy érvényes webcímet.']);
}

$query = http_build_query([
    'url' => $target,
    'output' => 'json',
    'fl' => 'timestamp,original,statuscode,mimetype,digest,length',
    'collapse' => 'digest',
    'limit' => '20',
]);
$query .= '&filter=statuscode%3A200&filter=mimetype%3Atext%2Fhtml';

$curl = curl_init('https://web.archive.org/cdx/search/cdx?' . $query);
curl_setopt_array($curl, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_FOLLOWLOCATION => true,
    CURLOPT_CONNECTTIMEOUT => 3,
    CURLOPT_TIMEOUT => 8,
    CURLOPT_USERAGENT => 'retro-kereso/1.0',
]);
$response = curl_exec($curl);
$status = curl_getinfo($curl, CURLINFO_HTTP_CODE);
$curlErrno = curl_errno($curl);
curl_close($curl);

if ($response === false && $curlErrno === CURLE_OPERATION_TIMEDOUT) {
    respond(504, ['error' => 'A Wayback Machine túl lassan válaszolt. Próbáld újra.']);
}

if ($response === false || $status < 200 || $status >= 300) {
    respond(502, ['error' => 'Nem sikerült elérni a Wayback Machine-t.']);
}

$rows = json_decode($response, true);
$items = [];
foreach (array_slice(is_array($rows) ? $rows : [], 1) as $row) {
    if (count($row) < 6) {
        continue;
    }
    [$timestamp, $original, $statusCode, $mimetype, $digest, $length] = $row;
    $items[] = [
        'timestamp' => $timestamp,
        'original' => $original,
        'status' => $statusCode,
        'mimetype' => $mimetype,
        'digest' => $digest,
        'length' => $length,
        'archiveUrl' => 'https://web.archive.org/web/' . rawurlencode($timestamp) . '/' . $original,
    ];
}

try {
    $database = database();
    $database->beginTransaction();
    $search = $database->prepare('INSERT INTO searches (query, searched_at) VALUES (:query, :searched_at)');
    $search->execute(['query' => $target, 'searched_at' => gmdate('c')]);
    $searchId = (int) $database->lastInsertId();
    $savedResult = $database->prepare('INSERT INTO results (search_id, timestamp, original, status, mimetype, digest, length, archive_url) VALUES (:search_id, :timestamp, :original, :status, :mimetype, :digest, :length, :archive_url)');
    foreach ($items as $item) {
        $savedResult->execute([
            'search_id' => $searchId,
            'timestamp' => $item['timestamp'],
            'original' => $item['original'],
            'status' => $item['status'],
            'mimetype' => $item['mimetype'],
            'digest' => $item['digest'],
            'length' => $item['length'],
            'archive_url' => $item['archiveUrl'],
        ]);
    }
    $database->commit();
} catch (Throwable) {
    respond(500, ['error' => 'A keresés naplózása nem sikerült.']);
}

respond(200, ['query' => $target, 'results' => $items]);
