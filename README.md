# Siete Pares Escrima — wiki export

A complete, self-contained export of the **Siete Pares Escrima** MediaWiki
(`home.sieteparesescrima.com`), taken **2026-10-21** from MediaWiki **1.35.2**.

The wiki was five years old, long past end of life, and effectively static —
39 revisions in 4.4 years, with a single edit in the last two. This export
preserves everything it held so the content can outlive the software.

## What's here

| Path | Contents |
|---|---|
| `xml/` | Full MediaWiki XML dumps — **the canonical copy** |
| `wikitext/` | Raw wikitext, one `.wiki` file per page (38) |
| `html/` | Rendered standalone HTML, one file per page (38) |
| `html/render/` | Body-only HTML per page — clean content, easy to re-theme |
| `images-flat/` | **All 24 uploads under their real filenames** — start here |
| `images/` | The same uploads in MediaWiki's hashed layout, for re-import |
| `assets/` | Skin CSS/JS bundles + logo, so `html/` is viewable offline |
| `db/content-tables.sql` | Content tables only — no users, no credentials |
| `config/settings-nonsecret.txt` | Non-secret `LocalSettings.php` values |
| `meta/` | Page list, upload inventory, extensions, skins, site info |

## Content

12 content pages, 24 images, 1 sidebar, plus File: description pages:

> Alamo City · Armado DEFTAC · Creed · Curriculum ·
> Grandmaster Nelson Estanol · Grandmasters · In Tribute · Main Page ·
> Masters · Members · Sinawali · Supreme Grandmaster

## Completeness — verified, not assumed

- Every upload recorded in the `image` table is present on disk (0 missing).
- `oldimage` is empty and `filearchive` is 0, so there are no prior file
  versions or deleted files that went uncaptured.
- All 38 pages produced wikitext, a full HTML render and a body render.
- Both a full-history and a current-revision XML dump are included.

Deliberately excluded as regenerable, not content: `l10n_cache` (1,053 MB of
localisation cache — ~99% of the old database's apparent size), `objectcache`,
`searchindex`, `querycache`, and the `images/thumb` + `images/temp` caches.

## Not included, by design

This is a **public** repository, so it contains no secrets and no personal data:

- No `LocalSettings.php` — it holds `$wgDBpassword`, `$wgSecretKey` and
  `$wgUpgradeKey`. Only non-secret settings are recorded, in `config/`.
- No `user`, `user_properties`, `actor`, `bot_passwords` or `oathauth_users`
  tables — those hold password hashes and email addresses. `db/content-tables.sql`
  is dumped from an explicit allow-list of content tables, so it is safe by
  construction rather than by redaction.

`.gitignore` also blocks the fuller local-only dumps by name.

## Restoring into a fresh MediaWiki

The XML dump is the canonical path and is version-independent:

```bash
php maintenance/importDump.php --no-updates < xml/sieteparesescrima-full-history.xml
php maintenance/rebuildrecentchanges.php
php maintenance/importImages.php /path/to/images-flat
php maintenance/rebuildall.php
```

Users are not restored — recreate the two accounts by hand.

## Provenance

Exported from MediaWiki 1.35.2 on MariaDB 10.3.39 and PHP
7.4.3-4ubuntu2.29+esm5 (Ubuntu 20.04). Produced with `dumpBackup.php`,
`getText.php`, `mysqldump` and HTTP renders of the live site.
