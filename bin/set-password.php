<?php

declare(strict_types=1);

function readHidden(string $prompt): string
{
    fwrite(STDOUT, $prompt);
    $canHide = DIRECTORY_SEPARATOR !== '\\' && function_exists('shell_exec');
    if ($canHide) {
        shell_exec('stty -echo 2>/dev/null');
    }
    $value = trim((string) fgets(STDIN));
    if ($canHide) {
        shell_exec('stty echo 2>/dev/null');
        fwrite(STDOUT, PHP_EOL);
    }
    return $value;
}

$password = getenv('RETRO_PASSWORD');
if (!is_string($password) || $password === '') {
    $password = readHidden('Új Retro Kereső jelszó: ');
    $confirm = readHidden('Jelszó még egyszer: ');
    if (!hash_equals($password, $confirm)) {
        fwrite(STDERR, "A két jelszó nem egyezik.\n");
        exit(1);
    }
}

if (strlen($password) < 12) {
    fwrite(STDERR, "A jelszó legyen legalább 12 karakteres.\n");
    exit(1);
}

$hash = password_hash($password, PASSWORD_DEFAULT);
if (!is_string($hash) || $hash === '') {
    fwrite(STDERR, "Nem sikerült a jelszó hash generálása.\n");
    exit(1);
}

$configPath = getenv('RETRO_CONFIG_PATH');
if (!is_string($configPath) || $configPath === '') {
    $configPath = dirname(__DIR__, 2) . '/retro-config.php';
}

$content = "<?php\n\ndeclare(strict_types=1);\n\nreturn [\n    'password_hash' => " . var_export($hash, true) . ",\n];\n";
$tmpPath = $configPath . '.tmp-' . bin2hex(random_bytes(4));

if (file_put_contents($tmpPath, $content, LOCK_EX) === false) {
    fwrite(STDERR, "Nem sikerült létrehozni az ideiglenes config fájlt.\n");
    exit(1);
}
@chmod($tmpPath, 0600);

if (!rename($tmpPath, $configPath)) {
    @unlink($tmpPath);
    fwrite(STDERR, "Nem sikerült frissíteni a config fájlt.\n");
    exit(1);
}
@chmod($configPath, 0600);

fwrite(STDOUT, "Kész. A jelszó hash biztonságosan elmentve ide: {$configPath}\n");
