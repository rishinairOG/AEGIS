const FirecrawlApp = require('@mendable/firecrawl-js').default;
const dotenv = require('dotenv');
const path = require('path');
const fs = require('fs');

// Load environment variables from .env
dotenv.config({ path: path.join(__dirname, '../../../.env') });

const apiKey = process.env.FIRECRAWL_API_KEY;

if (!apiKey) {
    console.error('Error: FIRECRAWL_API_KEY not found in environment or .env file.');
    process.exit(1);
}

const app = new FirecrawlApp({ apiKey });

const mode = process.argv[2];
const target = process.argv[3];

async function main() {
    try {
        switch (mode) {
            case 'scrape':
                console.log(`Scraping URL: ${target}...`);
                const scrapeResult = await app.scrapeUrl(target, { formats: ['markdown'] });
                if (scrapeResult.success) {
                    console.log('\n--- SCRAPE SUCCESS ---\n');
                    console.log(scrapeResult.markdown);
                } else {
                    console.error('Scrape failed:', scrapeResult.error);
                }
                break;

            case 'search':
                console.log(`Searching for: ${target}...`);
                const searchResult = await app.search(target, {
                    limit: 5,
                    scrapeOptions: { formats: ['markdown'] }
                });
                if (searchResult.success) {
                    console.log(`\n--- SEARCH SUCCESS (${searchResult.data.length} results) ---\n`);
                    searchResult.data.forEach((res, i) => {
                        console.log(`\nResult ${i + 1}: ${res.metadata.title || res.url}`);
                        console.log(`URL: ${res.url}`);
                        console.log(res.markdown.substring(0, 500) + '...');
                    });
                } else {
                    console.error('Search failed:', searchResult.error);
                }
                break;

            case 'map':
                console.log(`Mapping domain: ${target}...`);
                const mapResult = await app.mapUrl(target);
                if (mapResult.success) {
                    console.log('\n--- MAP SUCCESS ---\n');
                    console.log(mapResult.links.join('\n'));
                } else {
                    console.error('Map failed:', mapResult.error);
                }
                break;

            case 'crawl':
                console.log(`Starting crawl for: ${target}...`);
                const crawlResult = await app.crawlUrl(target, {
                    limit: 50,
                    scrapeOptions: { formats: ['markdown'] }
                });
                if (crawlResult.success) {
                    console.log('\n--- CRAWL STARTED ---\n');
                    console.log('Crawl ID:', crawlResult.id);
                    console.log('Use the ID to check status or wait for results if the SDK supports it sync (v4 does).');
                    // Note: In v4, crawlUrl might be async or sync depending on options.
                    // By default it returns immediately with an ID.
                    console.log('Response:', JSON.stringify(crawlResult, null, 2));
                } else {
                    console.error('Crawl failed:', crawlResult.error);
                }
                break;

            default:
                console.log('Usage: node firecrawl.js <mode> <target>');
                console.log('Modes: scrape, search, map, crawl');
                process.exit(1);
        }
    } catch (error) {
        console.error('Unexpected error:', error.message);
        process.exit(1);
    }
}

main();
