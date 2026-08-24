<?php

declare(strict_types=1);

$root = dirname(__DIR__);
$script = $root . '/bin/set-password.php';

if (!is_file($script)) {
    fwrite(STDERR, "FAIL: set-password.php missing\n");
    exit(1);
}

$tmp = sys_get_temp_dir() . '/retro-password-' . bin2hex(random_bytes(4));
mkdir($tmp, 0700, true);
$configPath = $tmp . '/retro-config.php';
$password = 'Example-Pass-123!';

$cmd = sprintf(
    'RETRO_CONFIG_PATH=%s RETRO_PASSWORD=%s php %s 2>&1',
    escapeshellarg($configPath),
    escapeshellarg($password),
    escapeshellarg($script)
);
exec($cmd, $output, $code);

if ($code !== 0) {
    fwrite(STDERR, "FAIL: script exited with $code\n" . implode("\n", $output) . "\n");
    exit(1);
}

$config = require $configPath;
$hash = $config['password_hash'] ?? '';
if (!is_string($hash) || $hash === '' || !password_verify($password, $hash)) {
    fwrite(STDERR, "FAIL: generated hash invalid\n");
    exit(1);
}

if (str_contains((string) file_get_contents($configPath), $password)) {
    fwrite(STDERR, "FAIL: plaintext password written to config\n");
    exit(1);
}

@unlink($configPath);
@rmdir($tmp);

echo "PASS: password setup script writes only a valid hash\n";
