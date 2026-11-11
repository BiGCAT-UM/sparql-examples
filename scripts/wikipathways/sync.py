"""Copy the WikiPathways example queries from wikipathways/SPARQLQueries.

SPARQLQueries keeps every WikiPathways example query as a Turtle file with an
identifier (WPQ036), a version, creators and parameters, and its CI publishes
them on the `examples-index` branch. This script reads that branch's
index.json and history.json and writes examples/WikiPathways/NNN.ttl for each
example WPQNNN, so the numbers and IRIs here stay what they were:

    https://bigcat-um.github.io/sparql-examples/WikiPathways/036
        owl:sameAs https://sparql.wikipathways.org/.well-known/sparql-examples/WPQ036

Each file records the version it was copied from (schema:version, and
dcterms:source pointing at the .ttl file at the commit of that version), and
where the query came from (prov:wasDerivedFrom: a web page or the old .rq file).
Parameterised examples run with their default values, which sit in a VALUES
block in the query. Deprecated examples are only kept if they were published
here before; an example is never removed.

    python scripts/wikipathways/sync.py           # update the files
    python scripts/wikipathways/sync.py --check   # exit 1 if anything would change
    python scripts/wikipathways/sync.py --index ../SPARQLQueries-index/   # a local copy

Edit the examples in SPARQLQueries, not here: these files are overwritten.
"""

import argparse
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import Namespace, RDFS

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT_DIR = REPO / "examples" / "WikiPathways"

INDEX = "https://raw.githubusercontent.com/wikipathways/SPARQLQueries/examples-index/"
EX_BASE = "https://bigcat-um.github.io/sparql-examples/WikiPathways/"
EDITOR = "https://sparql.wikipathways.org/?example="
SELF_REPO = "https://github.com/BiGCAT-UM/sparql-examples/"

SH = Namespace("http://www.w3.org/ns/shacl#")
SPEX = Namespace("https://purl.expasy.org/sparql-examples/ontology#")

# queryType in index.json -> (namespace prefix, class, query property)
QUERY_FORMS = {
    "select": ("sh", "SPARQLSelectExecutable", "select"),
    "ask": ("sh", "SPARQLAskExecutable", "ask"),
    "construct": ("sh", "SPARQLConstructExecutable", "construct"),
    "describe": ("spex", "SPARQLDescribeExecutable", "describe"),
}

IDENTIFIER = re.compile(r"^WPQ(\d{3,})$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def fetch_json(base, name):
    if re.match(r"^https?://", base):
        with urllib.request.urlopen(base.rstrip("/") + "/" + name, timeout=60) as r:
            return json.load(r)
    return json.loads((pathlib.Path(base) / name).read_text(encoding="utf-8"))


def turtle_string(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def turtle_long_string(text):
    text = text.replace("\\", "\\\\")
    # Escape quotes that would end the long string early or merge with the closing quotes.
    text = re.sub(r'"(?=""|"*$)', r'\\"', text)
    return '"""' + text + '"""'


def iri(value):
    value = str(value)
    if not re.match(r"^https?://", value) or re.search(r'[<>"{}|^`\\\s]', value):
        raise ValueError(f"not an IRI: {value!r}")
    return f"<{value}>"


def comment(example):
    text = example["description"].strip()
    params = sorted(example.get("params") or [], key=lambda p: p.get("order") or 0)
    if params:
        values = ", ".join(f'{p.get("label") or p["name"]} "{p["default"]}"' for p in params)
        text += (f" This example uses the default values ({values}); open it in the WikiPathways"
                 f" SPARQL editor to change them: {EDITOR}{example['id']}")
    if example.get("deprecated"):
        text += " This example is deprecated."
    return text


def keywords(example, category_labels):
    words = list(example.get("keywords") or [])
    for c in example.get("categories") or []:
        label = category_labels.get(c)
        if label and label.lower() not in (w.lower() for w in words):
            words.append(label.lower())
    return words


def version_commit(history, example):
    """The commit at which the example got its current version."""
    for entry in reversed(history.get("examples", {}).get(example["id"], [])):
        if entry.get("version") == example["version"]:
            return entry["commit"], entry["path"]
    raise ValueError(f"{example['id']}: version {example['version']} is not in history.json")


def render(number, example, history, repository, category_labels):
    form = QUERY_FORMS[example["queryType"]]
    query = example["query"].rstrip("\n")
    commit, path = version_commit(history, example)
    if not re.match(r"^[0-9a-f]{40}$", commit):
        raise ValueError(f"{example['id']}: bad commit {commit!r}")
    source = f"https://github.com/{repository}/blob/{commit}/{urllib.parse.quote(path)}"
    lines = [
        "@prefix dcterms: <http://purl.org/dc/terms/> .",
        f"@prefix ex: <{EX_BASE}> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix prov: <http://www.w3.org/ns/prov#> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix schema: <https://schema.org/> .",
        "@prefix sh: <http://www.w3.org/ns/shacl#> .",
        "@prefix spex: <https://purl.expasy.org/sparql-examples/ontology#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
        f"ex:{number} a sh:SPARQLExecutable,",
        f"       {form[0]}:{form[1]} ;",
        f"    rdfs:label {turtle_string(example['label'])}@en ;",
        f"    rdfs:comment {turtle_string(comment(example))}@en ;",
        "    sh:prefixes _:sparql_examples_prefixes ;",
        f"    {form[0]}:{form[2]} {turtle_long_string(query)} ;",
        f"    schema:target {iri(example['target'])} ;",
    ]
    words = keywords(example, category_labels)
    if words:
        lines.append("    schema:keywords " + ", ".join(turtle_string(w) for w in words) + " ;")
    for service in example.get("federatesWith") or []:
        lines.append(f"    spex:federatesWith {iri(service)} ;")
    for origin in example.get("derivedFrom") or []:
        # SPARQLQueries records the copy here that some examples started from; skip that loop.
        if not origin.startswith(SELF_REPO):
            lines.append(f"    prov:wasDerivedFrom {iri(origin)} ;")
    for reference in example.get("references") or []:
        lines.append(f"    dcterms:references {iri(reference)} ;")
    for person in example.get("creators") or []:
        lines.append(f"    dcterms:creator {iri(person['iri'])} ;")
    for person in example.get("contributors") or []:
        lines.append(f"    dcterms:contributor {iri(person['iri'])} ;")
    for field, prop in (("created", "created"), ("modified", "modified")):
        if example.get(field):
            if not DATE.match(example[field]):
                raise ValueError(f"{example['id']}: bad {field} {example[field]!r}")
            lines.append(f'    dcterms:{prop} "{example[field]}"^^xsd:date ;')
    lines.append(f"    schema:version {turtle_string(example['version'])} ;")
    if example.get("deprecated"):
        lines.append("    owl:deprecated true ;")
    lines.append(f"    owl:sameAs {iri(example['iri'])} ;")
    lines.append(f"    dcterms:source <{source}> ;")
    lines.append(f"    dcterms:license {iri(example['license'])} .")
    ttl = "\n".join(lines) + "\n"
    check_round_trip(number, ttl, query, form)
    return ttl


def check_round_trip(number, ttl, query, form):
    g = Graph()
    g.parse(data=ttl, format="turtle")
    subject = URIRef(EX_BASE + number)
    ns = SPEX if form[0] == "spex" else SH
    found = [str(o) for o in g.objects(subject, ns[form[2]])]
    if found != [query]:
        raise ValueError(f"{number}: query text does not survive the Turtle round trip")
    if not any(isinstance(o, Literal) for o in g.objects(subject, RDFS.comment)):
        raise ValueError(f"{number}: no rdfs:comment")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--index", default=INDEX,
                    help="URL or directory of the examples-index branch (default: %(default)s)")
    ap.add_argument("--check", action="store_true",
                    help="write nothing; exit with 1 if any file would change")
    args = ap.parse_args()

    index = fetch_json(args.index, "index.json")
    history = fetch_json(args.index, "history.json")
    if index.get("schema") != 1 or history.get("schema") != 1:
        sys.exit("unsupported index schema (this script reads schema 1)")
    repository = index["repository"]
    if not re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", repository):
        sys.exit(f"bad repository name {repository!r}")
    category_labels = {c["iri"]: c["label"] for c in index.get("categories", [])}

    changed, seen = [], set()
    for example in sorted(index["examples"], key=lambda e: e["id"]):
        m = IDENTIFIER.match(example["id"])
        if not m:
            sys.exit(f"unexpected identifier {example['id']!r}")
        number = m.group(1)
        seen.add(number)
        path = OUT_DIR / f"{number}.ttl"
        if example.get("deprecated") and not path.exists():
            continue
        ttl = render(number, example, history, repository, category_labels)
        if not path.exists() or path.read_text(encoding="utf-8") != ttl:
            changed.append(path.name)
            if not args.check:
                path.write_text(ttl, encoding="utf-8")

    orphans = sorted(p.name for p in OUT_DIR.glob("[0-9]*.ttl") if p.stem not in seen)
    if orphans:
        print("not in SPARQLQueries (left as they are): " + ", ".join(orphans), file=sys.stderr)

    print(f"{len(changed)} file(s) {'would change' if args.check else 'changed'} "
          f"(index of {index['commit'][:12]}, {len(index['examples'])} examples)")
    for name in changed:
        print("  " + name)
    if args.check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
