const FirecrawlApp = require('@mendable/firecrawl-js').default;
require('dotenv').config({ path: '../../.env' });

const app = new FirecrawlApp({ apiKey: process.env.FIRECRAWL_API_KEY });

async function run() {
    const url = 'https://firecrawl.dev';
    console.log(`Scraping ${url}...`);

    const scrapeResult = await app.scrapeUrl(url, {
        formats: ['markdown']
    });

    if (scrapeResult.success) {
        console.log('Markdown Content:');
        console.log(scrapeResult.markdown.substring(0, 500) + '...');
    } else {
        console.error('Error:', scrapeResult.error);
    }
}

run();
