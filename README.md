# Retro Kereső

Privát, jelszóval védett helyi Wayback-archívumkereső a pecscitythings.eu Hostinger tárhelyére.

A böngészős keresés nem élőben kérdezi le a Wayback Machine-t. A `bin/index-wayback.php` CLI indexelő előre letölti a konfigurált pécsi/környékbeli domainek archivált HTML oldalait, kinyeri a látható szöveget, és SQLite FTS5 indexbe menti. A webes kereső ezután gyorsan, helyben keres a mentett oldalak szövegében.

## Biztonság

A valódi hozzáférési jelszó **nem kerül a repóba**. Az alkalmazás csak PHP session után használható, és az API keresési végpontja is védett.

A jelszó hashét két módon lehet megadni:

1. `RETRO_PASSWORD_HASH` környezeti változóval; vagy
2. a `public_html` szülőkönyvtárában létrehozott `retro-config.php` fájlban.

A `retro-config.example.php` csak minta, valódi hash nem található benne.

A nyers Wayback HTML fájlok a `data/archive/` könyvtárba kerülnek. A `data/.htaccess` tiltja ezek közvetlen HTTP-kiszolgálását, és a snapshotok nincsenek verziókezelve.

## Hostinger telepítés

A repo webes fájljai a pecscitythings.eu `public_html` könyvtárába kerülnek. A `data` könyvtárnak PHP számára írhatónak kell lennie. A létrejövő `data/retro.sqlite` és `data/archive/` tartalma nincs verziókezelve.

### Jelszó beállítása

A szerveren a projekt könyvtárából futtasd:

```bash
php bin/set-password.php
```

A script kétszer bekéri a jelszót, `password_hash()` segítségével biztonságos hash-t készít, majd automatikusan létrehozza vagy frissíti a webrooton kívüli `retro-config.php` fájlt. A jelszó legalább 12 karakteres legyen.

## Archiválandó források

Az első verzió forráslistája:

```text
config/sources.php
```

A lista szándékosan külön van a UI-tól és az indexelőtől, így később egyszerűen bővíthető további pécsi/környékbeli domainekkel. Egy forráshoz `domain` és egy legfeljebb 200-as futásonkénti `limit` adható meg.

## FTS5 ellenőrzése

A helyi kereső SQLite FTS5-öt használ. Hostinger SSH-ban:

```bash
php -r '$db=new PDO("sqlite::memory:"); $db->exec("CREATE VIRTUAL TABLE t USING fts5(body)"); echo "FTS5 OK\n";'
```

Elvárt kimenet:

```text
FTS5 OK
```

## Wayback indexelés

A projekt gyökeréből:

```bash
php bin/index-wayback.php
```

Az indexelő:

- beolvassa a `config/sources.php` listát;
- domainenként bounded CDX lekérést végez;
- csak `200` státuszú HTML snapshotokat vesz figyelembe;
- a már indexelt URL + timestamp párokat kihagyja;
- letölti és helyben menti a nyers HTML-t;
- eltávolítja a nem kereshető `script`, `style`, `noscript` stb. tartalmat;
- SQLite FTS5 indexbe menti a címet és a látható szöveget;
- a végén kiírja az indexelt, kihagyott és hibás elemek számát.

Az első verzió kézzel indítható. Cron/automatikus futtatás későbbi bővítés.

## Böngészős keresés

A bejelentkezett UI kulcsszavakat vár, például:

```text
pécs
zsolnay
uránváros
széchenyi tér
```

A `GET /api.php?action=search&q=...` végpont csak a helyi SQLite FTS5 indexet kérdezi le; normál keresés közben nem hívja a Wayback Machine-t.

## Credits

The CDX sampling and Wayback downloading workflow was informed by ideas and behavior from these open-source projects:

- `jsvine/waybackpack`
- `hartator/wayback-machine-downloader`

This project does not claim that their source code was copied verbatim; the credit is for implementation ideas and workflow inspiration.

## Ellenőrzés

A feature telepítése után futtasd:

```bash
php tests/archive_schema_test.php
php tests/html_extract_test.php
php tests/source_config_test.php
php tests/archive_storage_test.php
php tests/indexer_contract_test.php
php tests/local_search_test.php
php tests/keyword_api_contract_test.php
php tests/keyword_ui_test.php
php tests/archive_exposure_test.php
php tests/auth_test.php
php tests/security_contract_test.php
php tests/set_password_test.php
php tests/simple_app_ui_test.php
php tests/login_minimal_test.php
php tests/asset_version_test.php

php -l lib/archive.php
php -l config/sources.php
php -l bin/index-wayback.php
php -l auth.php
php -l api.php
php -l index.php
php -l bin/set-password.php
```

Ha minden teszt `PASS`, a következő lépés az első kis indexelési futás a `php bin/index-wayback.php` paranccsal.
