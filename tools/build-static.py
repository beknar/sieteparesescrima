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


# Wiki controls that cannot work without MediaWiki behind them. Removed from
# the markup rather than hidden with CSS, so they are genuinely gone and cost
# nothing to download.
REMOVE_IDS = [
    # the whole Views tab strip: Read / Edit / Edit source / View history
    "p-views",
    # top-right personal tools: "Not logged in" / Talk / Contributions / Log in
    "p-personal",
    # the sidebar Tools portlet: What links here, Related changes, Special
    # pages, Printable version, Permanent link, Page information
    "p-tb",
    # the Page / Discussion namespace tabs
    "p-namespaces",
    # the search box — it needs a search backend to do anything
    "p-search",
    # the "Powered by MediaWiki" footer badge and its link
    "footer-icons",
    # footer links, all three of which were redlinks on the live wiki anyway:
    # Privacy policy, About Siete Pares Escrima, Disclaimers. The whole <ul>
    # goes, since removing its three items would leave an empty list.
    "footer-places",
    # three wiki links at the end of the Navigation portlet. The other 12
    # entries are this site's own nav (Creed, Sinawali, Grandmasters, ...) and
    # must survive, so these go individually rather than by removing p-navigation.
    "n-recentchanges",
    "n-randompage",
    "n-help-mediawiki",
]


def remove_element(doc, elem_id):
    """Drop the element carrying id="elem_id", including its children.

    MediaWiki's output is well-formed, so matching the element's own tag name
    while tracking nesting depth is reliable here and avoids a parser
    dependency (bs4/lxml are not installed on this host).
    """
    m = re.search(r'<(\w+)([^>]*\sid="%s")' % re.escape(elem_id), doc)
    if not m:
        return doc, False
    tag = m.group(1)
    start = m.start()

    # self-closing / void element
    open_end = doc.index(">", m.end() - 1)
    if doc[open_end - 1] == "/":
        return doc[:start] + doc[open_end + 1:], True

    depth = 0
    pos = start
    pat = re.compile(r"<(/?)%s\b" % re.escape(tag), re.I)
    while True:
        mm = pat.search(doc, pos)
        if not mm:
            return doc, False
        if mm.group(1):
            depth -= 1
            if depth == 0:
                end = doc.index(">", mm.end()) + 1
                return doc[:start] + doc[end:], True
        else:
            depth += 1
        pos = mm.end()


def remove_by_class(doc, tag, cls):
    """Remove every <tag class="...cls..."> element, children included.

    Used for the section edit links, which carry no id and nest further spans
    inside (the [ ] brackets), so a flat regex would stop at the first
    </span> and leave the brackets stranded.
    """
    pat = re.compile(r'<%s\b[^>]*class="[^"]*\b%s\b[^"]*"' % (re.escape(tag), re.escape(cls)))
    nest = re.compile(r"<(/?)%s\b" % re.escape(tag), re.I)
    removed = 0
    while True:
        m = pat.search(doc)
        if not m:
            return doc, removed
        depth, pos = 0, m.start()
        while True:
            mm = nest.search(doc, pos)
            if not mm:
                return doc, removed          # malformed; leave the rest alone
            if mm.group(1):
                depth -= 1
                if depth == 0:
                    end = doc.index(">", mm.end()) + 1
                    doc = doc[:m.start()] + doc[end:]
                    removed += 1
                    break
            else:
                depth += 1
            pos = mm.end()


def strip_wiki_controls(doc):
    for elem_id in REMOVE_IDS:
        doc, hit = remove_element(doc, elem_id)
        counts["removed " + elem_id if hit else "MISSING " + elem_id] += 1

    # The [edit] / [edit source] links beside headings. These sit in the page
    # content rather than the chrome, which is why removing the tab strip left
    # them behind.
    doc, n = remove_by_class(doc, "span", "mw-editsection")
    if n:
        counts["removed section edit links"] += n

    # MediaWiki's print-only "Retrieved from <url>" line. It is display:none on
    # screen, which is why it survived every visual check, but it carries an
    # absolute http:// link to an index.php URL that no longer exists -- so on
    # an HTTPS site it is both a dead link and the page's only mixed-content
    # reference. There is no live wiki to retrieve the page from any more, so
    # the whole line goes rather than being rewritten.
    doc, n = remove_by_class(doc, "div", "printfooter")
    if n:
        counts["removed print footer"] += n

    # Vector emits two screen-reader skip links. "Jump to search" now points at
    # a target that no longer exists, so it goes with the search box. "Jump to
    # navigation" aimed at #mw-head, which is empty now that its portlets are
    # gone, so repoint it at the sidebar where the nav actually lives.
    doc, hit = re.subn(
        r'<a class="mw-jump-link" href="#searchInput">[^<]*</a>\s*', "", doc)
    if hit:
        counts["removed jump-to-search link"] += hit
    doc, hit = re.subn(
        r'(<a class="mw-jump-link" href=")#mw-head(">)', r"\1#mw-panel\2", doc)
    if hit:
        counts["retargeted jump-to-nav link"] += hit
    return doc


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

    # srcset carries several comma-separated candidates, each "url 1.5x".
    # It needs the same treatment as src: uploads become relative, while skin
    # and resource paths move under static/.
    def srcset(m):
        parts = []
        for cand in m.group(2).split(","):
            cand = cand.strip()
            if not cand:
                continue
            bits = cand.split(None, 1)
            url, suffix = bits[0], (" " + bits[1] if len(bits) > 1 else "")
            if url.startswith("/images/"):
                counts["image"] += 1
                url = url.lstrip("/")
            elif url.startswith(("/skins/", "/resources/", "/extensions/")):
                counts["static asset"] += 1
                url = "static" + url.split("?")[0]
            parts.append(url + suffix)
        return 'srcset="%s"' % ", ".join(parts)

    doc = re.sub(r'(srcset)="([^"]*)"', srcset, doc)

    # --- internal page links ---
    for url in sorted(page_map, key=len, reverse=True):
        if url in doc:
            doc = doc.replace('"%s"' % url, '"%s"' % page_map[url])
            counts["page link"] += 1

    # --- drop the wiki controls, then pull the header up into the space they left ---
    doc = strip_wiki_controls(doc)
    doc = doc.replace(
        "</head>",
        '<link rel="stylesheet" href="assets/static-site.css"></head>', 1)
    counts["override css linked"] += 1

    # --- things that cannot work without a backend ---
    # drop the wiki's favicon link: it pointed at the wiki's own path. The
    # icon now lives at site/favicon.ico (the crest, added 2026-11-12), the
    # root path browsers request by default, so no link is needed
    doc = re.sub(r'<link[^>]*favicon[^>]*>', "", doc)
    doc = re.sub(r'<link[^>]*(?:opensearch_desc\.php|action=rsd)[^>]*>', "", doc)
    counts["stripped backend link"] += 1
    # <head>'s rel="edit" and application/x-wiki links point at ?action=edit,
    # which has nothing behind it here (crawlers follow them and get 404s)
    doc, n = re.subn(r'<link[^>]*action=edit[^>]*>', "", doc)
    counts["stripped edit link"] += n
    # the Recent changes Atom feed needs index.php too; and the generator tag
    # advertises a MediaWiki version that no longer runs here, which only
    # invites scanners to try its exploits
    doc, n = re.subn(r'<link rel="alternate" type="application/atom\+xml"[^>]*>', "", doc)
    counts["stripped feed link"] += n
    doc, n = re.subn(r'<meta name="generator" content="MediaWiki[^"]*"/>', "", doc)
    counts["stripped generator tag"] += n

    # File: pages credit the uploader as "Beknar (talk | contribs)": three
    # redlinks to user pages that were never created. Keep the name as text.
    doc, n = re.subn(r'<a [^>]*class="new mw-userlink"[^>]*>(<bdi>.*?</bdi>)</a>', r"\1", doc)
    counts["unlinked uploader"] += n
    doc, n = re.subn(r'<span style="white-space: nowrap;"> <span class="mw-usertoollinks">.*?</span></span>', "", doc)
    counts["removed talk/contribs links"] += n

    # ResourceLoader. bundle-3.js is its startup module, which only asks
    # load.php for the rest of the page's JS: every one of those requests
    # 404s here and the browser logs errors. Vector renders fine without JS,
    # so drop the loader and the inline RLCONF/RLQ scripts that feed it. The
    # first of those is also what flips <html> from client-nojs to client-js;
    # without it the page stays client-nojs, which matches having no JS.
    doc, n = re.subn(r'<script async="" src="assets/bundle-3\.js"></script>', "", doc)
    counts["removed ResourceLoader startup"] += n
    doc, n = re.subn(r'<script>(?:(?!</script>).)*?\b(?:RLCONF|RLQ)\b.*?</script>', "", doc, flags=re.S)
    counts["removed ResourceLoader inline scripts"] += n

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
