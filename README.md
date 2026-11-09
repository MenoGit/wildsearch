# WildSearch

A specialized search engine for hunting, wildlife, and outdoor recreation information.

WildSearch is a CS 454 Information Retrieval project developed by Emmanuel Ornelas Saucedo and Eden Alshanski.

## Planned Features

- Web crawling across public wildlife and government websites
- Full-text searching using Whoosh
- PageRank-based ranking
- Geographic search using hunting regions
- Advanced filters for species and hunting methods

## Current Progress

The initial Python breadth-first crawler has been adapted to support multiple domains.

Current functionality:

- Per-domain robots.txt checking
- HTML text and hyperlink extraction
- JSON document storage
- CSV hyperlink edge-list generation
- Basic HTTP redirect detection and skipping

The initial five-page crawl test completed successfully.

## Running the Crawler

```bash
python3 crawler.py
```

The crawler currently runs with a small page limit for testing.

**Status:** Early development. Large-scale crawling, complete redirect handling, PageRank, indexing integration, and the web interface are not yet implemented.
