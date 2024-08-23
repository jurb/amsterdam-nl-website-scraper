import aiohttp
import asyncio
from bs4 import BeautifulSoup
import os
import json
import pandas as pd
from urllib.parse import urljoin, urlparse
from collections import Counter, defaultdict
from tqdm import tqdm
import config as cfg

# Directories to save images and HTML pages
os.makedirs(cfg.IMAGE_DIR, exist_ok=True)
os.makedirs(cfg.HTML_DIR, exist_ok=True)

# Sets to track saved images and HTML pages
saved_images_set = set()
saved_html_set = set()

# Lists to track failed URLs
failed_pages = []
failed_images = []

async def save_image(session, url):
    """
    Download and save an image from the given URL.

    Args:
        session (aiohttp.ClientSession): The HTTP session to use for downloading.
        url (str): The URL of the image to download.

    Returns:
        str: The name of the saved image file or None if the download failed.
    """
    if url in saved_images_set:
        return os.path.basename(url)
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            content = await response.read()
            image_name = os.path.basename(urlparse(url).path)
            image_path = os.path.join(cfg.IMAGE_DIR, image_name)

            if not os.path.exists(image_path):
                with open(image_path, 'wb') as f:
                    f.write(content)
            saved_images_set.add(url)
            return image_name
    except Exception as e:
        print(f"Failed to download image {url}: {e}")
        failed_images.append(url)
        return None

def save_html(url, content):
    """
    Save the HTML content of a URL to a file.

    Args:
        url (str): The URL of the page.
        content (str): The HTML content to save.

    Returns:
        None
    """
    try:
        parsed_url = urlparse(url)
        if parsed_url.netloc == 'www.amsterdam.nl':
            html_name = parsed_url.path.replace('/', '_') + '.html'
            if html_name.startswith('_'):
                html_name = html_name[1:]
            html_path = os.path.join(cfg.HTML_DIR, html_name)

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(content)
            saved_html_set.add(url)
    except Exception as e:
        print(f"Failed to save HTML for {url}: {e}")
        failed_pages.append(url)

async def fetch_and_process_url(session, url):
    """
    Fetch and process a single URL to extract references and images.

    Args:
        session (aiohttp.ClientSession): The HTTP session to use for fetching.
        url (str): The URL to fetch and process.

    Returns:
        tuple: The URL and a dictionary with domains, reference URLs, and image URLs.
    """
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            page_content = await response.text()
            page_soup = BeautifulSoup(page_content, 'html.parser')

            # Save HTML content only if the domain is www.amsterdam.nl
            save_html(url, page_content)

            # Extract reference URLs and count them
            ref_urls = [urljoin(url, a['href']) for a in page_soup.find_all('a', href=True) if a['href'].startswith(('http://', 'https://'))]
            ref_url_counts = Counter(ref_urls)
            domain_counts = Counter(urlparse(ref_url).netloc for ref_url in ref_urls)

            # Extract images (collect image URLs, don't download yet)
            images = [urljoin(url, img['src']) for img in page_soup.find_all('img', src=True)]

            return url, {
                'domains': dict(domain_counts),  # Domains with counts
                'reference_urls': dict(ref_url_counts),  # URLs with counts
                'images': images  # Just collect image URLs for now
            }
    except Exception as e:
        print(f"Failed to process {url}: {e}")
        failed_pages.append(url)
        return url, None

async def process_images(image_urls):
    """
    Download and save images from the list of image URLs.

    Args:
        image_urls (list): A list of image URLs to download.

    Returns:
        list: A list of successfully saved image names.
    """
    async with aiohttp.ClientSession() as session:
        saved_images = await asyncio.gather(*[save_image(session, img_url) for img_url in image_urls])
    return [img for img in saved_images if img]  # Remove failed downloads

def convert_json_to_excel(json_file, excel_file):
    """
    Convert JSON data to an Excel file.

    Args:
        json_file (str): The file path of the JSON file.
        excel_file (str): The file path to save the Excel file.

    Returns:
        None
    """
    with open(json_file, 'r') as f:
        data = json.load(f)

    rows = []
    for url, details in data.items():
        domain_ref_urls = defaultdict(list)
        for ref_url, count in details['reference_urls'].items():
            domain = urlparse(ref_url).netloc
            domain_ref_urls[domain].append((ref_url, count))

        for domain, urls_counts in domain_ref_urls.items():
            for ref_url, count in sorted(urls_counts):
                rows.append({
                    'Page URL': url,
                    'Domain': domain,
                    'Reference URL': ref_url,
                    'Domain Count': details['domains'][domain],
                    'URL Count': count
                })

    df = pd.DataFrame(rows)
    df.to_excel(excel_file, index=False)
    print(f"Data saved to {excel_file}")

async def retry_failed_pages(session, max_retries=5):
    """
    Retry fetching and processing failed pages up to a maximum number of retries.

    Args:
        session (aiohttp.ClientSession): The HTTP session to use for fetching.
        max_retries (int): The maximum number of retry attempts.

    Returns:
        None
    """
    global failed_pages

    for attempt in range(max_retries):
        if not failed_pages:
            break  # Stop if there are no failed pages left

        print(f"\nRetrying failed pages (Attempt {attempt + 1}/{max_retries})...")
        retry_failed_pages = failed_pages
        failed_pages = []

        tasks = [fetch_and_process_url(session, url) for url in retry_failed_pages]

        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Retrying failed URLs"):
            await future

        if not failed_pages:
            break  # Stop if all retries succeeded

async def main(sitemap_url):
    """
    Main function to process the sitemap and extract data from each URL.

    Args:
        sitemap_url (str): The URL of the sitemap.

    Returns:
        None
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(sitemap_url) as response:
            response.raise_for_status()
            sitemap_content = await response.text()

    # Parse sitemap
    soup = BeautifulSoup(sitemap_content, 'lxml-xml')
    urls = [loc.text for loc in soup.find_all('loc')]

    # Dictionary to store the results
    data = {}
    all_image_urls = []

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_and_process_url(session, url) for url in urls]

        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing URLs"):
            url, result = await future
            if result:
                data[url] = result
                all_image_urls.extend(result['images'])  # Collect image URLs

        # Retry failed pages
        await retry_failed_pages(session, max_retries=5)

    # Process images separately
    print("Processing images...")
    saved_images = await process_images(all_image_urls)
    print(f"Total images processed: {len(saved_images)}")

    # Save results to JSON
    with open(os.path.join(cfg.BASE_DIR, 'scraped_data_overview.json'), 'w') as f:
        json.dump(data, f, indent=4)

    print("Scraping completed.")

    # Convert JSON data to Excel
    convert_json_to_excel(os.path.join(cfg.BASE_DIR, 'scraped_data_overview.json'), 
                          os.path.join(cfg.BASE_DIR, 'scraped_data_overview.xlsx'))

    # Write any remaining failed pages and images to files
    if failed_pages:
        with open(cfg.FAILED_HTML_FILE, 'w') as f:
            for page in failed_pages:
                f.write(f"{page}\n")
        print(f"Failed pages saved to {cfg.FAILED_HTML_FILE}")

    if failed_images:
        with open(cfg.FAILED_IMAGES_FILE, 'w') as f:
            for img in failed_images:
                f.write(f"{img}\n")
        print(f"Failed images saved to {cfg.FAILED_IMAGES_FILE}")

# Run the main function
sitemap_url = 'https://www.amsterdam.nl/sitemap.xml'
asyncio.run(main(sitemap_url))