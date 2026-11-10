# Use of JSON Pipeline

Every major NBER-CLI command supports `--format json`. This document shows how to chain commands into reproducible research pipelines.

## Stable JSON shapes

### `search --format json`

```json
{
  "results": [
    {"paper_id": "w25000", "title": "...", "authors": ["..."]}
  ],
  "pagination": {"page": 1, "per_page": 10, "total": 123}
}
```

### `info --format json`

```json
{
  "paper_id": "w25000",
  "title": "...",
  "authors": ["..."],
  "abstract": "...",
  "programs": ["..."]
}
```

### `feed fetch --format json`

```json
{
  "source_url": "https://www.nber.org/rss/new.xml",
  "database_path": "~/.nber-cli/nber.db",
  "total_fetched": 25,
  "new_count": 3,
  "display_all": false,
  "max_items": null,
  "items": [...]
}
```

## Build a citation list

```bash
uvx nber-cli search "gender wage gap" --format json \
  | jq -r '.results[] | "\(.authors | join(", ")) (\(.year // "n.d.")). \(.title). NBER Working Paper No. \(.paper_id)."' \
  > citations.txt
```

For one paper, use the built-in formatter instead of rebuilding the entry with `jq`. It supports six bibliography styles and handles author names and TeX escaping:

```bash
uvx nber-cli cite w25000 -f apa --stdout
```

## Extract abstracts for topic modeling

```bash
uvx nber-cli search "artificial intelligence" --format json \
  | jq -r '.results[].paper_id' \
  | while read -r id; do
      uvx nber-cli info "$id" --all --format json | jq -r '[.paper_id, .abstract] | @csv'
    done \
  > ai_abstracts.csv
```

## Feed-to-download pipeline

```bash
uvx nber-cli feed fetch --format json > /tmp/feed.json

if [ "$(jq '.new_count' /tmp/feed.json)" -gt 0 ]; then
  jq -r '.items[].paper_id' /tmp/feed.json \
    | xargs uvx nber-cli download --batch --save-base ./papers/new
fi
```

## Append-only JSON Lines log

```bash
uvx nber-cli feed fetch --format json \
  | jq -c '.items[]' >> nber_feed.jsonl
```

JSON Lines is convenient for `jq` streaming, DuckDB, or pandas ingestion.

## Validate with jq

```bash
uvx nber-cli info w25000 --format json | jq -e '.paper_id and .title'
```

The `-e` flag exits non-zero if the filter returns false or null, which is useful in shell conditionals.
