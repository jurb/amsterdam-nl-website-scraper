import os
import html2text
from bs4 import BeautifulSoup
from tqdm import tqdm
import concurrent.futures
import config as cfg

# Directories to save txt pages
os.makedirs(cfg.TXT_DIR, exist_ok=True)

def setup_html2text_converter():
    """
    Sets up and configures the html2text converter for condensed markdown output.
    
    Returns:
        html2text.HTML2Text: Configured converter instance.
    """
    h = html2text.HTML2Text()
    
    # Configure for condensed, clean markdown
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0  # Don't wrap lines
    h.unicode_snob = True
    h.skip_internal_links = False
    h.inline_links = True  # Use [text](url) format
    h.protect_links = True
    h.mark_code = True
    h.wrap_links = False
    h.wrap_list_items = False
    
    return h

def extract_main_content(filename, html_content):
    """
    Extracts the main content from HTML using CSS selectors.

    Args:
        filename (str): The name of the file being processed.
        html_content (str): The HTML content to be parsed.

    Returns:
        str: HTML content of the main section, or empty string if not found.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    main_content_selectors = [
        'div.content',
        'div.main-content', 
        'article',
        '#main',
        '.article',
    ]

    # Try each selector until we find content
    for selector in main_content_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            return str(main_content)
    
    # If no main content found, try to extract body content
    body = soup.find('body')
    if body:
        print(f"No main content selectors matched for {filename}, using body content")
        return str(body)
    
    print(f"No relevant content found for {filename}")
    return ""

def process_links(html_content, base_url="https://www.amsterdam.nl"):
    """
    Processes relative links to make them absolute.
    
    Args:
        html_content (str): HTML content to process.
        base_url (str): Base URL to prepend to relative links.
        
    Returns:
        str: HTML content with absolute links.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Fix relative links
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith('/') and not href.startswith('//'):
            link['href'] = base_url + href
    
    # Fix relative image sources
    for img in soup.find_all('img', src=True):
        src = img['src']
        if src.startswith('/') and not src.startswith('//'):
            img['src'] = base_url + src
    
    return str(soup)

def extract_page_title(html_content):
    """
    Extract the page title from Open Graph meta tag.
    
    Args:
        html_content (str): The HTML content to extract title from.
        
    Returns:
        str: The extracted page title, or None if not found.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Try to find og:title first
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        return og_title.get('content').strip()
    
    # Fallback to regular title tag
    title_tag = soup.find('title')
    if title_tag and title_tag.string:
        return title_tag.string.strip()
    
    return None

def create_page_link(filename, page_title=None):
    """
    Creates a page link using either the extracted page title or transformed filename.
    
    Args:
        filename (str): The HTML filename (without extension).
        page_title (str, optional): The extracted page title from og:title.
        
    Returns:
        str: The formatted page link.
    """
    # Create URL from filename (same as transform_string)
    input_string = filename.rstrip('_')
    url_path = input_string.replace('_', '/')
    url = f"https://www.amsterdam.nl/{url_path}/"
    
    # Use page title if available, otherwise transform filename
    if page_title:
        link_text = page_title
    else:
        # Fallback to transformed filename
        link_text = input_string.replace('-', ' ').replace('_', ' ')
    
    return f"[PAGE LINK: {link_text}]({url})"

def simple_condense(markdown_content):
    """
    Simple condensing using regex - much simpler than the full function.
    
    Args:
        markdown_content (str): Raw markdown content from html2text.
        
    Returns:
        str: Simply condensed markdown content.
    """
    import re
    
    # Remove multiple consecutive empty lines, replace with single empty line
    condensed = re.sub(r'\n\s*\n\s*\n+', '\n\n', markdown_content)
    
    # Remove trailing whitespace from each line
    condensed = '\n'.join(line.rstrip() for line in condensed.split('\n'))
    
    # Remove leading/trailing empty lines
    condensed = condensed.strip()
    
    return condensed

def process_html_file(file_path, filename, converter):
    """
    Processes an HTML file: creates PAGE LINK header using og:title + converts main content to condensed markdown.

    Args:
        file_path (str): Path to the HTML file.
        filename (str): Name of the HTML file.
        converter (html2text.HTML2Text): Configured converter instance.

    Returns:
        str: PAGE LINK header + condensed markdown content.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        # Extract page title from og:title meta tag
        page_title = extract_page_title(html_content)
        
        # Extract main content HTML
        main_html = extract_main_content(filename, html_content)
        if not main_html:
            return ""
        
        # Process links to make them absolute
        processed_html = process_links(main_html)
        
        # Convert to markdown using html2text
        markdown_content = converter.handle(processed_html)
        
        # Simple condensing (remove excessive empty lines)
        condensed_markdown = simple_condense(markdown_content)
        
        # Create the PAGE LINK header using extracted title
        base_name = os.path.splitext(filename)[0]
        page_link_header = create_page_link(base_name, page_title)
        
        # Combine PAGE LINK header with condensed markdown content
        final_content = f"{page_link_header}\n\n{condensed_markdown}"
        
        return final_content
        
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return ""

def load_html_content(directory, output_directory):
    """
    Loads HTML content from all files and converts to PAGE LINK + markdown format.

    Args:
        directory (str): Path to the directory containing HTML files.
        output_directory (str): Path to the directory where output text files will be saved.
    """
    # Set up the converter once
    converter = setup_html2text_converter()
    
    html_files = [f for f in os.listdir(directory) if f.endswith('.html')]
    
    for filename in tqdm(html_files, desc="Processing HTML files"):
        file_path = os.path.join(directory, filename)
        
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(process_html_file, file_path, filename, converter)
                processed_content = future.result(timeout=30)
            
            if processed_content:
                # Generate output filename
                base_name = os.path.splitext(filename)[0]
                output_file_path = os.path.join(output_directory, f"{base_name}.txt")
                
                with open(output_file_path, 'w', encoding='utf-8') as output_file:
                    output_file.write(processed_content)
            else:
                print(f"No content extracted from {filename}")
                
        except concurrent.futures.TimeoutError:
            print(f"Processing {filename} took too long and was skipped.")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

# Load and process HTML content
if __name__ == "__main__":
    load_html_content(cfg.HTML_DIR, cfg.TXT_DIR)