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
| `site/` | **Working static site** — open `site/index.html` |
| `tools/build-static.py` | Rebuilds `site/` from `html/` (URL rewrites only) |

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

## The static site (`site/`)

A self-contained static copy that is meant to look identical to the live wiki.
It is the exported Vector-skinned HTML with URLs rewritten — the markup and the
skin are untouched, which is what preserves the appearance.

```bash
python3 tools/build-static.py          # rebuild site/ from html/
cd site && python3 -m http.server 8088 # then open http://localhost:8088/
```

The build is idempotent, so re-running it is safe.

Verified: content bodies are byte-identical to the live wiki, all 27 CSS-
referenced skin assets load, the logo is byte-for-byte the live file, and every
local reference resolves (0 missing of 1046).

### What does not work, by design

The Vector chrome is preserved intact, so it still *renders* the wiki controls,
but they need a backend and therefore do nothing: the **Edit** and **View
history** tabs, the search box, **Log in**, and the sidebar's *Recent changes*,
*Random page* and *Special pages*. The footer's *Privacy policy*, *About* and
*General disclaimer* links were already redlinks on the live wiki.

Two genuine losses versus the wiki: full-text search (the box needs a backend —
a small JS index over 12 pages would replace it) and browser-based editing.

### Gotcha worth remembering

The CSS bundles come straight off `load.php`, so their internal `url()` values
are absolute (`/skins/...`) or root-relative (`resources/...`). Both 404 when
served as plain files — which silently removes the logo, the search icon,
sidebar bullets, tab fades, arrows and the thumbnail magnify icons. Rewriting
the HTML alone is not enough; `build-static.py` rewrites the stylesheets too.
