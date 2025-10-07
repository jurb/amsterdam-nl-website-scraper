# Amsterdam.nl Web Scraper

Scrape www.amsterdam.nl and convert HTML to clean text or markdown. Uses asynchronous requests for efficient scraping. Includes retry logic for failed URLs and whitelisted user agent for /subsidies pages

<figure align="center">
  <img src="media/homescreen.png" alt="amsterdam.nl homescreen">
</figure>

## Installation

```bash
git clone https://github.com/Amsterdam-AI-Team/amsterdam-nl-website-scraper.git
cd amsterdam-nl-website-scraper
pip install -r requirements.txt
```

Tested with Python 3.10.0 on Linux/MacOS/Windows.

## Usage

### Basic scraping (entire sitemap, blocked unless whitelisted)

```bash
cd src
python3 scrape_amsterdam_nl.py
```

### Scrape specific sections using JSON index (recommended for partial whitelisted user agents)

```bash
cd src
python3 scrape_amsterdam_nl.py --json_index_url "https://www.amsterdam.nl/subsidies/subsidies-alfabet?new_json=true&pager_rows=500"
```

### Scrape with path filter

Works with both sitemap and JSON index:

```bash
python3 scrape_amsterdam_nl.py --sitemap_url https://www.amsterdam.nl/sitemap.xml --path_filter /subsidies
python3 scrape_amsterdam_nl.py --json_index_url "https://www.amsterdam.nl/subsidies/subsidies-alfabet?new_json=true&pager_rows=500" --path_filter /subsidies
```

### Convert HTML to text or markdown

```bash
python3 html_to_txt.py    # Plain text
python3 html_to_md.py     # Markdown (better for LLMs)
```

### Using `uv` (no installation needed)

```bash
cd src
uv run --with beautifulsoup4 --with aiohttp --with pandas --with tqdm --with lxml --with openpyxl --with asyncio --with brotli scrape_amsterdam_nl.py --json_index_url "https://www.amsterdam.nl/subsidies/subsidies-alfabet?new_json=true&pager_rows=500"
uv run --with beautifulsoup4 --with tqdm --with html2text html_to_md.py
```

## Features

- **JSON index support**: Scrape specific sections by URL pattern
- **Path filtering**: Filter URLs by path (works with sitemap or JSON index)
- **Retry logic**: Automatically retries failed URLs (with/without trailing slash)
- **Whitelisted bot**: Uses `SubsidiemaatjeBot` user agent
- **Async scraping**: Efficient parallel downloading
- **Multiple output formats**: Plain text or markdown conversion

## Contributing

Feel free to help out! [Open an issue](https://github.com/Amsterdam-AI-Team/amsterdam-nl-website-scraper/issues), submit a [PR](https://github.com/Amsterdam-AI-Team/amsterdam-nl-website-scraper/pulls) or [contact us](https://amsterdamintelligence.com/contact/).


## Acknowledgements

This repository was created by [Amsterdam Intelligence](https://amsterdamintelligence.com/) for the City of Amsterdam.

## License 

This project is licensed under the terms of the European Union Public License 1.2 (EUPL-1.2).

