<?php

declare(strict_types=1);

$index = file_get_contents(__DIR__ . '/../index.php');

function requireCondition(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

$loginStart = strpos($index, '<?php if (!$authenticated): ?>');
$loginEnd = strpos($index, '<?php else: ?>', $loginStart === false ? 0 : $loginStart);
requireCondition($loginStart !== false && $loginEnd !== false, 'login branch must exist');
$loginMarkup = substr($index, $loginStart, $loginEnd - $loginStart);

foreach (['PRIVATE ARCHIVE', 'A régi web', 'Belépés után', 'Hozzáférési jelszó', 'WAYBACK MACHINE', 'PRIVATE ACCESS', '>R<', '>W<'] as $visibleText) {
    requireCondition(strpos($loginMarkup, $visibleText) === false, "login page must not show text: {$visibleText}");
}
requireCondition(strpos($loginMarkup, 'id="password"') !== false, 'password field must remain');
requireCondition(strpos($loginMarkup, 'type="submit"') !== false, 'submit button must remain');

fwrite(STDOUT, "PASS\n");
