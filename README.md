# Amsterdam.nl Web Scraper

Scripts to scrape contents (text and images) from www.amsterdam.nl and process the HTML into clean text files.

## Background

These scripts are designed to scrape and process the contents of the Amsterdam.nl website, extracting text and images for analysis and archival purposes. The project makes use of asynchronous requests to efficiently handle multiple pages and resources.

## Folder Structure

* `data`: Stores sample data and output files from the scraping process.
* `docs`: Additional documentation if required.
* `notebooks`: Jupyter notebooks for tutorials or exploratory analysis.
* `res`: Resources such as images used for documentation.
* `scripts`: Contains scripts for automating various tasks related to the project.
* `src`: All source code files specific to this project.
* `tests`: Unit tests to validate the functionality of the code.

## Installation

1. Clone this repository:

    ```bash
    git clone https://github.com/Amsterdam-AI-Team/amsterdam_nl_website_scraper.git
    ```

2. Install all dependencies:

    ```bash
    pip install -r requirements.txt
    ```

    The code has been tested with Python 3.x on Linux/MacOS/Windows.

## Usage

### Step 1: Scrape HTML and Images

First, use the `scrape_amsterdam_nl.py` script to scrape HTML pages and images from the Amsterdam.nl website.

1. Ensure the URLs to scrape are defined in the configuration file.
2. Run the script:

    ```bash
    python scrape_amsterdam_nl.py
    ```

   This will download and save all HTML pages and images from the specified URLs into designated directories.

### Step 2: Convert HTML to Text

After scraping, use the `html_to_txt.py` script to convert the downloaded HTML pages into clean text files.

1. Ensure the scraped HTML files are in the directory specified in the configuration.
2. Run the script:

    ```bash
    python html_to_txt.py
    ```

   This will process the HTML files, extracting the main content and saving it as text files.

## How it works

### Input

- **scrape_amsterdam_nl.py**: Fetches HTML content and images from URLs defined in the configuration.
- **html_to_txt.py**: Takes the scraped HTML files from a specified directory.

### Algorithm

1. **scrape_amsterdam_nl.py**:
   - Utilizes asynchronous HTTP requests to efficiently scrape and save HTML pages and images.
   - Tracks saved content to avoid redundancy and records any failed downloads.

2. **html_to_txt.py**:
   - Uses BeautifulSoup to parse HTML files, extracting main content based on predefined selectors.
   - Processes the extracted content to handle links and dynamic elements, saving the result as clean text files.

### Output

- **scrape_amsterdam_nl.py**: Saves HTML pages and images into designated directories, with logs of any failed downloads.
- **html_to_txt.py**: Outputs text files containing the cleaned main content of the HTML pages.

## Contribution

Contributions are welcome. Please submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.
