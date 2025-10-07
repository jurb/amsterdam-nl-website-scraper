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
import ssl
import argparse

# Directories to save images and HTML pages
os.makedirs(cfg.IMAGE_DIR, exist_ok=True)
os.makedirs(cfg.HTML_DIR, exist_ok=True)

# Sets to track saved images and HTML pages
saved_images_set = set()
saved_html_set = set()

# Lists to track failed URLs
failed_pages = []
failed_images = []

def get_url_alternative(url):
    """
    Get the alternative version of a URL (add/remove trailing slash).
    
    Args:
        url (str): The original URL.
    
    Returns:
        str: The alternative URL with opposite slash behavior.
    """
    if not url:
        return url
    
    # Don't modify URLs that are just the root (e.g., "https://example.com/")
    parsed = urlparse(url)
    if parsed.path == '/' or parsed.path == '':
        return url
    
    # Toggle trailing slash
    if url.endswith('/'):
        return url.rstrip('/')
    else:
        return url + '/'

def get_html_file_name(url):
    """
    Generate the expected HTML file name from a URL.
    Always normalizes to version without trailing slash for consistent file naming.

    Args:
        url (str): The URL to generate the file name for.

    Returns:
        str or None: The expected HTML file name, or None if not applicable.
    """
    # Always normalize to version without trailing slash for consistent file naming
    if url.endswith('/') and not url.endswith('//'):
        parsed = urlparse(url)
        if parsed.path != '/':  # Don't modify root URLs
            url = url.rstrip('/')
    
    parsed_url = urlparse(url)
    if parsed_url.netloc == 'www.amsterdam.nl':
        html_name = parsed_url.path.replace('/', '_') + '.html'
        if html_name.startswith('_'):
            html_name = html_name[1:]
        return html_name
    else:
        return None

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

def is_error_page(soup, url, content_length):
    """
    Check if the parsed HTML content represents an error page.
    Now includes more detailed logging for debugging.

    Args:
        soup (BeautifulSoup): The parsed HTML content.
        url (str): The URL being checked (for logging).
        content_length (int): Length of the content.

    Returns:
        bool: True if it's an error page, False otherwise.
    """
    # Check for common error indicators
    title = soup.title.string if soup.title else ''
    error_titles = [
        "Internal Server Error",
        "Error",
        "Page Not Found", 
        "404 Not Found",
        "Access Denied",
        "Service Unavailable"
    ]
    
    title_has_error = any(error_title in title for error_title in error_titles)
    if title_has_error:
        print(f"DEBUG: Error detected in title for {url}: '{title}'")
        return True

    # Check for specific error messages in the body
    error_messages = [
        "An error occurred on the server",
        "We apologize for the problem", 
        "The page you are looking for doesn't exist",
        "This page cannot be found",
        "You don't have permission to access",
        "Service is temporarily unavailable"
    ]
    
    body_text = soup.get_text()
    message_has_error = any(error_message in body_text for error_message in error_messages)
    if message_has_error:
        print(f"DEBUG: Error message detected in body for {url}")
        return True

    # Check if content is suspiciously short (might indicate an error page)
    if content_length < 500:
        print(f"DEBUG: Suspiciously short content for {url}: {content_length} chars")
        print(f"DEBUG: Title: '{title}'")
        print(f"DEBUG: First 200 chars of body: '{body_text[:200]}'")
        # Don't automatically reject short content, just log it
        
    return False

def save_html(url, content):
    """
    Save the HTML content of a URL to a file, unless it's an error page.
    Enhanced with better debugging.

    Args:
        url (str): The URL of the page.
        content (str): The HTML content to save.

    Returns:
        bool: True if the page was saved, False if it was an error page.
    """
    try:
        soup = BeautifulSoup(content, 'html.parser')

        # Check if the page is an error page with enhanced debugging
        if is_error_page(soup, url, len(content)):
            print(f"Detected error page at {url}. Skipping save.")
            failed_pages.append(url)
            return False

        html_name = get_html_file_name(url)
        if html_name:
            html_path = os.path.join(cfg.HTML_DIR, html_name)

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(content)
            saved_html_set.add(url)
            print(f"DEBUG: Successfully saved HTML for {url} ({len(content)} chars)")
        return True
    except Exception as e:
        print(f"Failed to save HTML for {url}: {e}")
        failed_pages.append(url)
        return False

def extract_data_from_content(url, content):
    """
    Extract data from HTML content.

    Args:
        url (str): The URL of the page.
        content (str): The HTML content.

    Returns:
        tuple: The URL and a dictionary with domains, reference URLs, and image URLs.
    """
    try:
        page_soup = BeautifulSoup(content, 'html.parser')

        # Check if the page is an error page
        if is_error_page(page_soup, url, len(content)):
            print(f"Detected error page at {url}. Skipping processing.")
            failed_pages.append(url)
            return url, None

        # Extract reference URLs and count them (preserve URLs as they appear)
        ref_urls = []
        for a in page_soup.find_all('a', href=True):
            href = a['href']
            if href.startswith(('http://', 'https://')):
                full_url = urljoin(url, href)
                ref_urls.append(full_url)
        
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
        print(f"Failed to extract data from {url}: {e}")
        failed_pages.append(url)
        return url, None

async def fetch_and_process_url(session, url):
    """
    Fetch and process a single URL to extract references and images.
    Enhanced with better debugging and error handling.

    Args:
        session (aiohttp.ClientSession): The HTTP session to use for fetching.
        url (str): The URL to fetch and process.

    Returns:
        tuple: The URL and a dictionary with domains, reference URLs, and image URLs.
    """
    urls_to_try = [url, get_url_alternative(url)]
    last_exception = None
    
    print(f"DEBUG: Processing {url}")
    print(f"DEBUG: Will try URLs: {urls_to_try}")
    
    for attempt_url in urls_to_try:
        try:
            print(f"DEBUG: Attempting to fetch {attempt_url}")
            async with session.get(attempt_url) as response:
                print(f"DEBUG: Got response {response.status} for {attempt_url}")
                print(f"DEBUG: Response headers: {dict(response.headers)}")
                
                response.raise_for_status()
                page_content = await response.text()
                
                print(f"DEBUG: Got {len(page_content)} chars of content from {attempt_url}")
                
                # Check if content is meaningful (not just empty or minimal)
                if len(page_content.strip()) < 100:
                    print(f"Got minimal content from {attempt_url}, trying alternative...")
                    continue

                # Save HTML content only if it's not an error page
                # Use original URL for consistent file naming
                if not save_html(url, page_content):
                    # If it's an error page, skip processing
                    print(f"DEBUG: Skipping {url} due to error page detection")
                    return url, None

                # Extract data from content
                print(f"Successfully fetched {attempt_url}")
                return extract_data_from_content(url, page_content)
                
        except Exception as e:
            print(f"Failed to fetch {attempt_url}: {type(e).__name__}: {e}")
            last_exception = e
            continue
    
    # If we get here, both attempts failed
    print(f"Failed to process {url} with both trailing slash variants. Last error: {last_exception}")
    failed_pages.append(url)
    return url, None

async def process_existing_html(url):
    """
    Process an existing HTML file to extract data.

    Args:
        url (str): The URL corresponding to the HTML file.

    Returns:
        tuple: The URL and a dictionary with domains, reference URLs, and image URLs.
    """
    try:
        html_name = get_html_file_name(url)
        if html_name:
            html_path = os.path.join(cfg.HTML_DIR, html_name)
            with open(html_path, 'r', encoding='utf-8') as f:
                page_content = f.read()

            # Extract data from content
            return extract_data_from_content(url, page_content)
        else:
            print(f"No HTML file name for {url}")
            failed_pages.append(url)
            return url, None
    except Exception as e:
        print(f"Failed to process existing HTML for {url}: {e}")
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
    # Create session with proper headers for image downloads too
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    connector = aiohttp.TCPConnector(ssl=False, limit=10)
    headers = {
        'User-Agent': 'SubsidiemaatjeBot',
        'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,nl;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-origin',
    }
    
    async with aiohttp.ClientSession(timeout=timeout, connector=connector, headers=headers) as session:
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
        retry_failed_pages_list = failed_pages.copy()
        failed_pages = []

        tasks = [fetch_and_process_url(session, url) for url in retry_failed_pages_list]

        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Retrying failed URLs"):
            url, result = await future
            if result:
                data[url] = result  # Update data with the result
                all_image_urls.extend(result['images'])  # Collect image URLs

        if not failed_pages:
            break  # Stop if all retries succeeded

def create_session():
    """
    Create an aiohttp session with browser-like headers and proper configuration.
    
    Returns:
        aiohttp.ClientSession: Configured session
    """
    # Browser-like headers with whitelisted user agent
    headers = {
        'User-Agent': 'SubsidiemaatjeBot',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9,nl;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    # Timeout configuration (increase timeouts)
    timeout = aiohttp.ClientTimeout(total=60, connect=15)
    
    # SSL configuration (disable SSL verification if needed)
    connector = aiohttp.TCPConnector(
        ssl=False,  # Try with SSL disabled first
        limit=10,   # Limit concurrent connections
        force_close=True,
        enable_cleanup_closed=True
    )
    
    return aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        headers=headers
    )

async def main(sitemap_url=None, json_index_url=None, additional_urls=[], path_filter=None):
    """
    Main function to process the sitemap/index and extract data from each URL.
    Enhanced with better session configuration.

    Args:
        sitemap_url (str): The URL of the sitemap.
        json_index_url (str): The URL of a JSON index (e.g., with ?new_json=true&pager_rows=500).
        additional_urls (list): A list of additional URLs to process.
        path_filter (str): Optional path filter to only scrape URLs containing this path (e.g., '/subsidies').

    Returns:
        None
    """
    global data, all_image_urls
    data = {}
    all_image_urls = []

    urls = []

    if json_index_url:
        async with create_session() as session:
            async with session.get(json_index_url) as response:
                response.raise_for_status()
                json_content = await response.text()

        # Parse JSON index
        json_data = json.loads(json_content)
        json_urls = [item['source_url'] for item in json_data if 'source_url' in item]

        # Apply path filter if specified
        if path_filter:
            filtered_urls = [url for url in json_urls if path_filter in urlparse(url).path]
            urls.extend(filtered_urls)
            print(f"Found {len(json_urls)} URLs in JSON index, {len(filtered_urls)} matching path filter '{path_filter}'")
        else:
            urls.extend(json_urls)
            print(f"Found {len(json_urls)} URLs in JSON index")

    elif sitemap_url:
        async with create_session() as session:
            async with session.get(sitemap_url) as response:
                response.raise_for_status()
                sitemap_content = await response.text()

        # Parse sitemap
        soup = BeautifulSoup(sitemap_content, 'lxml-xml')
        sitemap_urls = [loc.text for loc in soup.find_all('loc')]

        # Apply path filter if specified
        if path_filter:
            filtered_urls = [url for url in sitemap_urls if path_filter in urlparse(url).path]
            urls.extend(filtered_urls)
            print(f"Found {len(sitemap_urls)} URLs in sitemap, {len(filtered_urls)} matching path filter '{path_filter}'")
        else:
            urls.extend(sitemap_urls)
            print(f"Found {len(sitemap_urls)} URLs in sitemap")

    # Add additional URLs
    urls.extend(additional_urls)

    # Read failed URLs from failed_html.txt and add them to the list
    failed_html_path = cfg.FAILED_HTML_FILE
    if os.path.exists(failed_html_path):
        with open(failed_html_path, 'r') as f:
            failed_urls = [line.strip() for line in f if line.strip()]
            urls.extend(failed_urls)
            print(f"Added {len(failed_urls)} URLs from {failed_html_path}")

    # Remove duplicates
    urls = list(set(urls))
    print(f"Total unique URLs to process: {len(urls)}")

    # Load existing HTML file names
    existing_html_files = set(os.listdir(cfg.HTML_DIR))

    # Prepare lists for URLs to scrape and URLs to process from existing HTML
    urls_to_scrape = []
    urls_to_process = []

    for url in urls:
        html_name = get_html_file_name(url)
        if html_name and html_name in existing_html_files:
            print(f"HTML exists for {url}, will process existing file.")
            urls_to_process.append(url)
        else:
            urls_to_scrape.append(url)

    # Process URLs with existing HTML files
    print(f"Processing {len(urls_to_process)} URLs from existing HTML files...")
    existing_tasks = [process_existing_html(url) for url in urls_to_process]
    for future in tqdm(asyncio.as_completed(existing_tasks), total=len(existing_tasks), desc="Processing existing HTML"):
        url, result = await future
        if result:
            data[url] = result
            all_image_urls.extend(result['images'])  # Collect image URLs

    # Scrape and process new URLs
    if urls_to_scrape:
        print(f"Scraping and processing {len(urls_to_scrape)} new URLs...")
        async with create_session() as session:
            tasks = [fetch_and_process_url(session, url) for url in urls_to_scrape]

            for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing new URLs"):
                url, result = await future
                if result:
                    data[url] = result
                    all_image_urls.extend(result['images'])  # Collect image URLs

            # Retry failed pages
            await retry_failed_pages(session, max_retries=10)
    else:
        print("No new URLs to scrape.")

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

    # Write any remaining failed pages and images to files (overwrite failed_html.txt)
    if failed_pages:
        with open(cfg.FAILED_HTML_FILE, 'w') as f:
            for page in failed_pages:
                f.write(f"{page}\n")
        print(f"Failed pages saved to {cfg.FAILED_HTML_FILE}")
    else:
        # If no failed pages, ensure failed_html.txt is empty
        open(cfg.FAILED_HTML_FILE, 'w').close()
        print(f"No failed pages. {cfg.FAILED_HTML_FILE} has been cleared.")

    if failed_images:
        with open(cfg.FAILED_IMAGES_FILE, 'w') as f:
            for img in failed_images:
                f.write(f"{img}\n")
        print(f"Failed images saved to {cfg.FAILED_IMAGES_FILE}")
    else:
        # If no failed images, ensure failed_images.txt is empty
        open(cfg.FAILED_IMAGES_FILE, 'w').close()
        print(f"No failed images. {cfg.FAILED_IMAGES_FILE} has been cleared.")

if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Scrape amsterdam.nl website')
    parser.add_argument('--path_filter', type=str, default=None,
                        help='Only scrape URLs containing this path (e.g., /subsidies) - only works with --sitemap_url')
    parser.add_argument('--sitemap_url', type=str, default=None,
                        help='URL of the sitemap to scrape (default: https://www.amsterdam.nl/sitemap.xml)')
    parser.add_argument('--json_index_url', type=str, default=None,
                        help='URL of a JSON index page (e.g., https://www.amsterdam.nl/subsidies/subsidies-alfabet?new_json=true&pager_rows=500)')
    args = parser.parse_args()

    # Default to sitemap if neither is specified
    if not args.sitemap_url and not args.json_index_url:
        args.sitemap_url = 'https://www.amsterdam.nl/sitemap.xml'

    # List of additional URLs to process
    additional_urls = [
        # Add more URLs as needed
    ]

    asyncio.run(main(sitemap_url=args.sitemap_url, json_index_url=args.json_index_url,
                     additional_urls=additional_urls, path_filter=args.path_filter))