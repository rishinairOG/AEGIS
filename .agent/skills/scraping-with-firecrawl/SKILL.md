---
name: scraping-with-firecrawl
description: "Efficiently scrape, crawl, search, and map websites into clean Markdown for AI workflows using Firecrawl."
---

# Scraping with Firecrawl

This skill enables the agent to interact with the Firecrawl API to convert web content into clean, LLM-ready Markdown.

## Core Capabilities

- **Scrape**: Convert a single URL into clean Markdown.
- **Crawl**: Recursively traverse a website and extract content from all subpages.
- **Search**: Perform a web search and scrape the top results directly into Markdown.
- **Map**: Generate a comprehensive sitemap/list of URLs for a given domain.

## Usage Requirements

- **API Key**: Requires `FIRECRAWL_API_KEY` to be set in the `.env` file.
- **SDK**: Uses `@mendable/firecrawl-js`.

## Detailed Modes

### 1. Scrape (Single Page)
Use this when you need precise content from one specific URL.
```javascript
const response = await app.scrapeUrl(url, { formats: ['markdown'] });
```

### 2. Crawl (Full Site)
Use this to gather information across an entire domain. You can limit depth and specify subpath filters.
```javascript
const crawlResponse = await app.crawlUrl(url, {
  limit: 100,
  scrapeOptions: { formats: ['markdown'] }
});
```

### 3. Search (Scrape Results)
Use this for broad research tasks where you need the content of the top search results.
```javascript
const searchResponse = await app.search(query, {
  limit: 5,
  scrapeOptions: { formats: ['markdown'] }
});
```

### 4. Map (Discovery)
Use this to quickly identify all pages on a website without scraping them yet.
```javascript
const mapResponse = await app.mapUrl(url);
```

## Implementation Notes
- Always check the status of crawl jobs as they are asynchronous for large sites.
- Prefer `markdown` format for LLM consumption.
- Use the provided helper script `scripts/firecrawl.js` for quick CLI-based scraping.
