# Retro Kereső

Privát Wayback Machine kereső a pecscitythings.eu Hostinger tárhelyére.

## Biztonság

A valódi hozzáférési jelszó **nem kerül a repóba**. Az alkalmazás csak PHP session után használható, és az API keresési végpontja is védett.

A jelszó hashét két módon lehet megadni:

1. `RETRO_PASSWORD_HASH` környezeti változóval; vagy
2. a `public_html` szülőkönyvtárában létrehozott `retro-config.php` fájlban.

A `retro-config.example.php` csak minta, valódi hash nem található benne.

## Hostinger telepítés

A repo webes fájljai a pecscitythings.eu `public_html` könyvtárába kerülnek. A `data` könyvtárnak PHP számára írhatónak kell lennie. A létrejövő `data/retro.sqlite` nincs verziókezelve és közvetlen HTTP-hozzáférése tiltott.

### Jelszó beállítása

A szerveren a projekt könyvtárából futtasd:

```bash
php bin/set-password.php
```

A script kétszer bekéri a jelszót, `password_hash()` segítségével biztonságos hash-t készít, majd automatikusan létrehozza vagy frissíti a webrooton kívüli `retro-config.php` fájlt. A jelszó legalább 12 karakteres legyen.

## Ellenőrzés

```bash
php tests/auth_test.php
php tests/security_contract_test.php
php tests/set_password_test.php
php -l auth.php
php -l api.php
php -l index.php
php -l bin/set-password.php
```
