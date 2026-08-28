<?php

// Másold ezt a fájlt a public_html SZÜLŐKÖNYVTÁRÁBA retro-config.php néven.
// A jelszót soha ne tárold itt olvasható formában; csak password_hash() kimenetet használj.
return [
    'password_hash' => '$2y$12$REPLACE_WITH_A_REAL_PASSWORD_HASH',

    // Megosztott titok a crawler sync szkriptje (crawler/sync_to_hostinger.py)
    // számára, hogy feltölthesse az újonnan talált oldalakat az archívumba.
    // Generálj sajátot, pl.: python -c "import secrets; print(secrets.token_urlsafe(32))"
    'ingest_token' => 'REPLACE_WITH_A_LONG_RANDOM_TOKEN',

    // Opcionális: ha be van állítva, az archívum a helyi SQLite helyett
    // ezt a MySQL/MariaDB szervert használja (pl. a Synology NAS-on futó
    // adatbázist, amelyet a crawler is feltölt).
    'mysql' => [
        'host' => '192.168.1.2',
        'port' => 3306,
        'database' => 'retrocrawler',
        'user' => 'retrocrawler',
        'password' => 'REPLACE_WITH_REAL_PASSWORD',
    ],
];
