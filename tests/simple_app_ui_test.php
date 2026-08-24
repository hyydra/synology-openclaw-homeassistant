<?php

declare(strict_types=1);

$index = file_get_contents(__DIR__ . '/../index.php');

function requireSimpleUi(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

requireSimpleUi(strpos($index, 'id="searchForm"') !== false, 'search form must remain');
requireSimpleUi(strpos($index, 'id="url"') !== false, 'URL input must remain');
requireSimpleUi(strpos($index, 'id="results"') !== false, 'results container must remain');
requireSimpleUi(strpos($index, 'class="hero-copy"') === false, 'large hero section must be removed');
requireSimpleUi(strpos($index, '<h1 id="appTitle">') === false, 'large app heading must be removed');

fwrite(STDOUT, "PASS\n");
