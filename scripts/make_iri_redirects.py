#!/usr/bin/env python3
"""Write redirect pages so that the example IRIs resolve on GitHub Pages.

An example such as https://bigcat-um.github.io/sparql-examples/WikiPathways/001 is
rendered at examples/WikiPathways/001, so its IRI itself gives a 404. For every example
IRI under the site, this script writes a small HTML page at the IRI path
(WikiPathways/001.html, which GitHub Pages also serves as WikiPathways/001) that
forwards to the rendered page. The namespace itself (WikiPathways/) forwards to the
folder index. Existing files are never overwritten unless they are redirect pages
written by this script.

The publish workflow runs it before the Jekyll build:

    python scripts/make_iri_redirects.py [--out DIR]
"""

import argparse
import html
import json
import pathlib
import sys

from rdflib import Graph, Namespace, RDF

SITE = "https://bigcat-um.github.io/sparql-examples/"
SH = Namespace("http://www.w3.org/ns/shacl#")
MARKER = "<!-- redirect written by scripts/make_iri_redirects.py -->"

PAGE = """<!DOCTYPE html>
{marker}
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<link rel="canonical" href="{url}">
<meta http-equiv="refresh" content="0; url={url}">
<meta name="robots" content="noindex">
<script>location.replace({url_js});</script>
</head>
<body>
<p>This SPARQL example is at <a href="{url}">{url}</a>.</p>
</body>
</html>
"""


def redirects(root):
    """Map output path (relative to the site root) to target URL."""
    result = {}
    for ttl in sorted(root.glob("examples/*/*.ttl")):
        graph = Graph()
        graph.parse(ttl, format="turtle")
        for subject in graph.subjects(RDF.type, SH.SPARQLExecutable):
            iri = str(subject)
            if not iri.startswith(SITE):
                continue
            path = iri[len(SITE):]
            folder = f"examples/{ttl.parent.name}/"
            if path.startswith(folder) or "/" not in path:
                continue
            result[path + ".html"] = SITE + folder + ttl.stem
            result[path.rsplit("/", 1)[0] + "/index.html"] = SITE + folder
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("."),
                    help="site root to write the pages to (default: current directory)")
    args = ap.parse_args()

    written = skipped = 0
    for path, url in sorted(redirects(pathlib.Path(".")).items()):
        out = args.out / path
        if out.exists() and MARKER not in out.read_text(encoding="utf-8", errors="replace"):
            print(f"skipping {path}: a file that is not a redirect page is already there", file=sys.stderr)
            skipped += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(PAGE.format(marker=MARKER, title=html.escape(path.removesuffix(".html")),
                                   url=html.escape(url), url_js=json.dumps(url)), encoding="utf-8")
        written += 1
    print(f"wrote {written} redirect pages" + (f", skipped {skipped}" if skipped else ""))


if __name__ == "__main__":
    main()
