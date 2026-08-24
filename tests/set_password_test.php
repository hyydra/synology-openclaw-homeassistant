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

putenv('RETRO_CONFIG_PATH=' . $configPath);
putenv('RETRO_PASSWORD=' . $password);
require $script;
putenv('RETRO_CONFIG_PATH');
putenv('RETRO_PASSWORD');

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
