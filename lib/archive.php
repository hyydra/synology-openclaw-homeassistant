<?php

declare(strict_types=1);

function retroArchiveDatabase(?string $path = null): PDO
{
    $path ??= dirname(__DIR__) . '/data/retro.sqlite';
    $directory = dirname($path);
    if (!is_dir($directory) && !mkdir($directory, 0770, true) && !is_dir($directory)) {
        throw new RuntimeException('Az archívum adatkönyvtára nem hozható létre.');
    }

    $db = new PDO('sqlite:' . $path, null, null, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
    $db->exec('PRAGMA foreign_keys = ON');
    $db->exec('PRAGMA busy_timeout = 5000');
    return $db;
}

function retroRequireFts5(PDO $db): void
{
    try {
        $db->exec('CREATE VIRTUAL TABLE temp.retro_fts5_probe USING fts5(body)');
        $db->exec('DROP TABLE temp.retro_fts5_probe');
    } catch (Throwable $error) {
        throw new RuntimeException('A szerveren az SQLite FTS5 nem érhető el.', 0, $error);
    }
}

function retroEnsureArchiveSchema(PDO $db): void
{
    retroRequireFts5($db);

    $db->exec(<<<'SQL'
CREATE TABLE IF NOT EXISTS archive_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_key TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    original_url TEXT NOT NULL,
    wayback_timestamp TEXT NOT NULL,
    archive_url TEXT NOT NULL,
    local_path TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    content_text TEXT NOT NULL DEFAULT '',
    indexed_at TEXT NOT NULL,
    UNIQUE(original_url, wayback_timestamp)
)
SQL);

    $db->exec(<<<'SQL'
CREATE VIRTUAL TABLE IF NOT EXISTS archive_pages_fts USING fts5(
    title,
    content_text,
    content='archive_pages',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
)
SQL);

    $db->exec(<<<'SQL'
CREATE TRIGGER IF NOT EXISTS archive_pages_ai AFTER INSERT ON archive_pages BEGIN
  INSERT INTO archive_pages_fts(rowid, title, content_text)
  VALUES (new.id, new.title, new.content_text);
END
SQL);

    $db->exec(<<<'SQL'
CREATE TRIGGER IF NOT EXISTS archive_pages_ad AFTER DELETE ON archive_pages BEGIN
  INSERT INTO archive_pages_fts(archive_pages_fts, rowid, title, content_text)
  VALUES ('delete', old.id, old.title, old.content_text);
END
SQL);

    $db->exec(<<<'SQL'
CREATE TRIGGER IF NOT EXISTS archive_pages_au AFTER UPDATE ON archive_pages BEGIN
  INSERT INTO archive_pages_fts(archive_pages_fts, rowid, title, content_text)
  VALUES ('delete', old.id, old.title, old.content_text);
  INSERT INTO archive_pages_fts(rowid, title, content_text)
  VALUES (new.id, new.title, new.content_text);
END
SQL);
}

function retroArchiveSnapshotKey(string $originalUrl, string $timestamp): string
{
    return hash('sha256', $originalUrl . "\n" . $timestamp);
}

/** @return array{title:string,text:string} */
function retroExtractArchivedPage(string $html): array
{
    if ($html === '') {
        return ['title' => '', 'text' => ''];
    }

    $previous = libxml_use_internal_errors(true);
    try {
        $document = new DOMDocument();
        $loaded = $document->loadHTML('<?xml encoding="UTF-8">' . $html, LIBXML_NOERROR | LIBXML_NOWARNING | LIBXML_NONET);
        if (!$loaded) {
            return ['title' => '', 'text' => ''];
        }

        $xpath = new DOMXPath($document);
        foreach (['script', 'style', 'noscript', 'template', 'svg'] as $tag) {
            $nodes = $xpath->query('//' . $tag);
            if ($nodes === false) {
                continue;
            }
            $toRemove = [];
            foreach ($nodes as $node) {
                $toRemove[] = $node;
            }
            foreach ($toRemove as $node) {
                $node->parentNode?->removeChild($node);
            }
        }

        $title = '';
        $titleNodes = $document->getElementsByTagName('title');
        if ($titleNodes->length > 0) {
            $title = retroNormalizeArchiveText((string) $titleNodes->item(0)?->textContent);
        }

        $body = $document->getElementsByTagName('body')->item(0);
        $text = retroNormalizeArchiveText((string) ($body?->textContent ?? $document->textContent));
        return ['title' => $title, 'text' => $text];
    } finally {
        libxml_clear_errors();
        libxml_use_internal_errors($previous);
    }
}

function retroNormalizeArchiveText(string $text): string
{
    $text = html_entity_decode($text, ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $text = preg_replace('/[\p{Z}\s]+/u', ' ', $text) ?? $text;
    return trim($text);
}
