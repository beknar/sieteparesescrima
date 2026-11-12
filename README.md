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

### Wiki controls removed

Everything that needed MediaWiki behind it is **removed from the markup**, not
hidden with CSS, so it is genuinely gone and costs nothing to download:

| Area | Removed |
|---|---|
| Tab strip | Read, Edit, Edit source, View history (`p-views`) |
| | Page, Discussion (`p-namespaces`) |
| Top right | Not logged in, Talk, Contributions, Log in (`p-personal`) |
| | The search box (`p-search`) |
| Sidebar | Recent changes, Random page, Help about MediaWiki |
| | The whole **Tools** portlet (`p-tb`) |
| Footer | Privacy policy, About, Disclaimers (`footer-places`) |
| | Powered by MediaWiki (`footer-icons`) |
| Content | The `[edit]` / `[edit source]` links beside headings |
| | On the 24 `File:` pages, the uploader's `talk` / `contribs` redlinks (the name `Beknar` stays, as text) |
| `<head>` | The `rel="edit"` / `application/x-wiki` links, the Recent changes Atom feed, and the `MediaWiki 1.35.2` generator tag |
| Scripts | ResourceLoader: the startup module (`assets/bundle-3.js`) and the inline `RLCONF` / `RLQ` scripts |

What remains: the logo, the 12 site navigation links, the page content, and the
footer's "This page was last edited on ..." line. Pages are about 40% smaller
than the raw export.

Two consequences worth stating plainly: there is **no search** (a small JS index
over 12 pages would restore it) and **no browser editing** — the wiki averaged
one edit every two years, so neither was in real use.

No old wiki UI is left (2026-11-12): a crawl of the live site finds no broken
links.

### Why the scripts went

ResourceLoader's startup module exists only to ask `load.php` for the rest of
a page's JavaScript, so on a static host every page logged a string of 404s.
Vector renders without JavaScript, and nothing on these pages needs it, so the
build drops the loader and its inline scripts. The first inline script is also
what switches `<html>` from `client-nojs` to `client-js`; with it gone, the
pages stay `client-nojs`, which is accurate. The one visible side effect is on
the `File:` pages, where MediaWiki's JS collapsed the rarer EXIF rows;
`static-site.css` keeps them collapsed. `assets/bundle-3.js` is left in
`site/assets/` but nothing references it.

### Accessibility note

Vector emits two screen-reader skip links. "Jump to search" was removed with the
search box it targeted. "Jump to navigation" pointed at `#mw-head`, which is
empty now that its portlets are gone, so the build repoints it at `#mw-panel`
where the navigation actually lives — rather than dropping it and losing the
affordance.

### Gotcha worth remembering

The CSS bundles come straight off `load.php`, so their internal `url()` values
are absolute (`/skins/...`) or root-relative (`resources/...`). Both 404 when
served as plain files — which silently removes the logo, sidebar bullets, tab
fades, arrows and the thumbnail magnify icons. Rewriting the HTML alone is not
enough; `build-static.py` rewrites the stylesheets too.

`srcset` needs the same treatment as `src`, and is easy to miss: a responsive
image can keep working off its `src` while every `srcset` candidate 404s.

The section edit links carry no `id` and nest spans inside for the `[` `]`
brackets, so a flat regex stops at the first `</span>` and leaves stray
brackets beside the headings. The build removes them depth-aware.
