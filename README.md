# Amsterdam.nl Web Scraper

Scripts to scrape contents (text and images) from www.amsterdam.nl and process the HTML into clean text files.

| ![Homescreen](./media/homescreen.png) |
|:---:|

## Background

These scripts are designed to scrape and process the contents of the Amsterdam.nl website, extracting text and images for analysis and archival purposes. The project makes use of asynchronous requests to efficiently handle multiple pages and resources.

## Folder Structure

 * [`scripts`](./sripts) _Scraper scripts_

## Installation

1. Clone this repository:

    ```bash
    git clone https://github.com/Amsterdam-AI-Team/amsterdam_nl_website_scraper.git
    ```

2. Install all dependencies:

    ```bash
    pip install -r requirements.txt
    ```

    The code has been tested with Python 3.10.0 on Linux/MacOS/Windows.

## Usage

### Step 1: Scrape HTML and Images

First, use the `scrape_amsterdam_nl.py` script to scrape HTML pages and images from the Amsterdam.nl website.

1. Run the script:

    ```bash
    python scrape_amsterdam_nl.py
    ```

   This will download and save all HTML pages and images from the specified URLs into designated directories.

### Step 2: Convert HTML to Text

After scraping, use the `html_to_txt.py` script to convert the downloaded HTML pages into clean text files.

1. Run the script:

    ```bash
    python html_to_txt.py
    ```

   This will process the HTML files, extracting the main content and saving it as text files.

## Contributing

Feel free to help out! [Open an issue](https://github.com/Amsterdam-AI-Team/Accessible_Route_Planning/issues), submit a [PR](https://github.com/Amsterdam-AI-Team/Accessible_Route_Planning/pulls) or [contact us](https://amsterdamintelligence.com/contact/).


## Acknowledgements

This repository was created by [Amsterdam Intelligence](https://amsterdamintelligence.com/) for the City of Amsterdam.

## License 

This project is licensed under the terms of the European Union Public License 1.2 (EUPL-1.2).

