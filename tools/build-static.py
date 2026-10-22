#!/usr/bin/env python3
"""Turn the MediaWiki HTML export in html/ into a self-contained static site in site/.

Rewrites only URLs — the markup and the Vector skin are left alone, so the
result is meant to look identical to the live wiki. Run from the repo root:

    python3 tools/build-static.py

Inputs : html/*.html, images/, site/assets/, site/static/, tools/asset-map.tsv
Output : site/*.html
"""

import html
import os
import re
import shutil
import sys
import urllib.parse
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

OUT = "site"
counts = Counter()


def page_filename(title):
    """Same mapping the export used, so links line up with the files on disk."""
    return re.sub(r"[/:]", "_", title).replace(" ", "_") + ".html"


def load_titles():
    with open("meta/page-titles.txt", encoding="utf-8") as fh:
        return [l.strip() for l in fh if l.strip()]


def load_asset_map():
    """load.php URL -> local file. Keyed on the raw and the &amp; form."""
    m = {}
    with open("tools/asset-map.tsv", encoding="utf-8") as fh:
        for line in fh:
            url, local = line.rstrip("\n").split("\t")
            m[url] = local
            m[url.replace("&", "&amp;")] = local
    return m


def build_page_map(titles):
    """Every URL form a page link can take -> its local .html file."""
    m = {}
    for t in titles:
        f = page_filename(t)
        u = t.replace(" ", "_")
        for key in (u, urllib.parse.quote(u), urllib.parse.quote(u, safe=""), html.escape(u)):
            m["/index.php/" + key] = f
    return m


def rewrite(doc, page_map, asset_map):
    # --- load.php bundles (longest first, they share a prefix) ---
    for url in sorted(asset_map, key=len, reverse=True):
        if url in doc:
            doc = doc.replace(url, asset_map[url])
            counts["load.php"] += 1

    # --- skin/resource assets: /skins/... /resources/... -> static/..., query dropped ---
    def static_ref(m):
        counts["static asset"] += 1
        return '%s="static%s"' % (m.group(1), m.group(2))

    doc = re.sub(r'(src|href)="(/(?:skins|resources|extensions)/[^"?]*)(?:\?[^"]*)?"',
                 static_ref, doc)

    # --- uploads and thumbnails: already relative-able, just strip the leading slash ---
    def image_ref(m):
        counts["image"] += 1
        return '%s="%s"' % (m.group(1), m.group(2).lstrip("/"))

    doc = re.sub(r'(src|srcset|href)="(/images/[^"]*)"', image_ref, doc)

    # srcset carries several comma-separated candidates
    def srcset(m):
        parts = []
        for cand in m.group(2).split(","):
            cand = cand.strip()
            if cand.startswith("/images/"):
                counts["image"] += 1
                cand = cand.lstrip("/")
            parts.append(cand)
        return 'srcset="%s"' % ", ".join(parts)

    doc = re.sub(r'(srcset)="([^"]*)"', srcset, doc)

    # --- internal page links ---
    for url in sorted(page_map, key=len, reverse=True):
        if url in doc:
            doc = doc.replace('"%s"' % url, '"%s"' % page_map[url])
            counts["page link"] += 1

    # --- things that cannot work without a backend ---
    # the live wiki 404s on /favicon.ico too, so drop the link rather than
    # leave a reference to a file that does not exist
    doc = re.sub(r'<link[^>]*favicon[^>]*>', "", doc)
    doc = re.sub(r'<link[^>]*(?:opensearch_desc\.php|action=rsd)[^>]*>', "", doc)
    counts["stripped backend link"] += 1

    return doc


def rewrite_css(path):
    """Rewrite url() refs inside a CSS bundle to point at static/.

    The bundles come straight off load.php, so their url() values are absolute
    ("/skins/...") or root-relative ("resources/..."). Both 404 once served as
    plain files, which is what hid the logo and every skin icon. The bundles
    live in site/assets/, so static/ is one level up.
    """
    with open(path, encoding="utf-8", errors="replace") as fh:
        css = fh.read()

    def repl(m):
        quote, ref = m.group(1), m.group(2)
        # "../static/" means this bundle was already rewritten; leave it be so
        # the build stays idempotent and re-runs do not stack prefixes.
        if ref.startswith(("data:", "http://", "https://", "//", "#", "../static/")):
            return m.group(0)
        clean = ref.split("?")[0].split("#")[0].lstrip("/")
        counts["css url()"] += 1
        return "url(%s../static/%s%s)" % (quote, clean, quote)

    css = re.sub(r'url\((["\']?)([^)"\']+)\1\)', repl, css)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(css)


def main():
    titles = load_titles()
    page_map = build_page_map(titles)
    asset_map = load_asset_map()

    os.makedirs(OUT, exist_ok=True)

    for name in sorted(os.listdir(os.path.join(OUT, "assets"))):
        if name.endswith(".css"):
            rewrite_css(os.path.join(OUT, "assets", name))

    # uploads + thumbs live beside the pages
    if os.path.isdir("images"):
        dst = os.path.join(OUT, "images")
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree("images", dst,
                        ignore=shutil.ignore_patterns(".htaccess", "README", "lockdir"))

    n = 0
    for name in sorted(os.listdir("html")):
        if not name.endswith(".html"):
            continue
        with open(os.path.join("html", name), encoding="utf-8", errors="replace") as fh:
            doc = fh.read()
        doc = rewrite(doc, page_map, asset_map)
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
            fh.write(doc)
        n += 1

    # Main_Page is the entry point
    main_page = os.path.join(OUT, "Main_Page.html")
    if os.path.exists(main_page):
        shutil.copyfile(main_page, os.path.join(OUT, "index.html"))

    print("pages written: %d" % n)
    for k, v in sorted(counts.items()):
        print("  %-24s %d" % (k, v))

    # --- verification: nothing absolute should be left pointing at the wiki ---
    leftovers = Counter()
    for name in os.listdir(OUT):
        if not name.endswith(".html"):
            continue
        with open(os.path.join(OUT, name), encoding="utf-8") as fh:
            doc = fh.read()
        for m in re.findall(r'(?:src|href)="(/[^"]*)"', doc):
            leftovers[m.split("?")[0]] += 1
        for m in re.findall(r'(?:src|href)="(https?://home\.sieteparesescrima\.com[^"]*)"', doc):
            leftovers["ABS " + m.split("?")[0]] += 1

    if leftovers:
        print("\nremaining absolute refs (dead wiki UI is expected here):")
        for k, v in leftovers.most_common(12):
            print("  %5d  %s" % (v, k))
    else:
        print("\nno absolute refs remain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
