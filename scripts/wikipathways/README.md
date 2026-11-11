# WikiPathways examples

`examples/WikiPathways/` holds every public example query for the WikiPathways SPARQL endpoint. They
are copies: the examples are maintained in [wikipathways/SPARQLQueries](https://github.com/wikipathways/SPARQLQueries),
where each one has an identifier (`WPQ036`), a version, creators and parameters, and is shown in the
[WikiPathways SPARQL editor](https://sparql.wikipathways.org/). Edit them there, not here.

Example `NNN` here is example `WPQNNN` there, so the IRIs in this repository stay what they were:

    https://bigcat-um.github.io/sparql-examples/WikiPathways/036
        owl:sameAs https://sparql.wikipathways.org/.well-known/sparql-examples/WPQ036

## Updating

SPARQLQueries' CI publishes its examples on the `examples-index` branch. `sync.py` reads that and
rewrites the files here:

```bash
pip install rdflib
python scripts/wikipathways/sync.py           # update the files
python scripts/wikipathways/sync.py --check   # exit 1 if anything would change
```

The workflow `sync-wikipathways.yml` does this every Monday (or on demand from the Actions tab),
runs the SPARQL checks, and opens a pull request when something changed.

Examples are never removed. A deprecated example (`owl:deprecated true`) stays if it was published
here, and is not added if it was not; that is why `WPQ084` and `WPQ085` (neXtProt) have no file.

## What a file records

- the query, label, description, target endpoint, keywords and federated endpoints;
- the version it was copied from: `schema:version`, and `dcterms:source` pointing at the `.ttl`
  file in SPARQLQueries at the commit of that version;
- creators and contributors (ORCID where known), `dcterms:created` and `dcterms:modified`;
- `prov:wasDerivedFrom`: the web page or the old `.rq` file the query came from.

Parameterised examples run with their default values, which sit in a `VALUES` block in the query;
the description links to the editor, where the values can be changed.

Until 2026-11-11 the files were generated from SPARQLQueries' `.rq` files by `rq2ttl.py`, with
`sources.tsv` mapping numbers to sources (including the queries on the WikiPathways website). Both are
in this repository's history at `ead7c0b`.
