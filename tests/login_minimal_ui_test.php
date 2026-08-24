<?php

declare(strict_types=1);

$index = file_get_contents(dirname(__DIR__) . '/index.php');
if (!is_string($index)) {
    fwrite(STDERR, "FAIL: index.php missing\n");
    exit(1);
}

// The unauthenticated view must contain only the password form UI.
$loginStart = strpos($index, '<?php if (!$authenticated): ?>');
$appStart = strpos($index, '<?php else: ?>', $loginStart === false ? 0 : $loginStart);
if ($loginStart === false || $appStart === false) {
    fwrite(STDERR, "FAIL: login/app conditional structure missing\n");
    exit(1);
}

$loginMarkup = substr($index, $loginStart, $appStart - $loginStart);
foreach (['build-version', 'Credits:', 'waybackpack', 'wayback-machine-downloader'] as $forbidden) {
    if (str_contains($loginMarkup, $forbidden)) {
        fwrite(STDERR, "FAIL: login view contains info text marker {$forbidden}\n");
        exit(1);
    }
}

foreach (['id="password"', 'id="loginForm"', 'id="loginError"'] as $required) {
    if (!str_contains($loginMarkup, $required)) {
        fwrite(STDERR, "FAIL: login view missing {$required}\n");
        exit(1);
    }
}

fwrite(STDOUT, "PASS\n");
