<?php

declare(strict_types=1);

require __DIR__ . '/../auth.php';

function assertTrue(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

$hash = password_hash('correct horse battery staple', PASSWORD_DEFAULT);
assertTrue(is_string($hash), 'test hash should be generated');
assertTrue(retroVerifyPassword('correct horse battery staple', $hash), 'correct password should verify');
assertTrue(!retroVerifyPassword('wrong password', $hash), 'wrong password should fail');

putenv('RETRO_PASSWORD_HASH=' . $hash);
assertTrue(retroPasswordHash() === $hash, 'password hash should load from environment');
putenv('RETRO_PASSWORD_HASH');

fwrite(STDOUT, "PASS\n");
