<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/archive.php';

$tmp = sys_get_temp_dir() . '/retro-sources-' . bin2hex(random_bytes(4)) . '.php';
file_put_contents($tmp, <<<'PHP'
<?php
return [
  ['domain' => 'PECS.HU', 'limit' => 150],
  ['domain' => 'pecs.hu', 'limit' => 9999],
  ['domain' => 'pte.hu', 'limit' => 80],
  ['domain' => 'https://invalid.example/path', 'limit' => 10],
  ['domain' => '', 'limit' => 10],
];
PHP);

$sources = retroLoadSources($tmp);
@unlink($tmp);

if (count($sources) !== 2) {
    fwrite(STDERR, "FAIL: expected two valid unique sources\n");
    exit(1);
}
if ($sources[0]['domain'] !== 'pecs.hu' || $sources[0]['limit'] !== 200) {
    fwrite(STDERR, "FAIL: source normalization/bounding\n");
    exit(1);
}
if ($sources[1]['domain'] !== 'pte.hu' || $sources[1]['limit'] !== 80) {
    fwrite(STDERR, "FAIL: second source parsing\n");
    exit(1);
}

fwrite(STDOUT, "PASS\n");
