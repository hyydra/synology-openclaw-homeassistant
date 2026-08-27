<?php

// Másold ezt a fájlt a public_html SZÜLŐKÖNYVTÁRÁBA retro-config.php néven.
// A jelszót soha ne tárold itt olvasható formában; csak password_hash() kimenetet használj.
return [
    'password_hash' => '$2y$12$REPLACE_WITH_A_REAL_PASSWORD_HASH',

    // Megosztott titok a crawler sync szkriptje (crawler/sync_to_hostinger.py)
    // számára, hogy feltölthesse az újonnan talált oldalakat az archívumba.
    'ingest_token' => 'PxJi5j6ExfHcCpdbFBgTNMg98NkQLft0HKMy3_PlFKc',
];
