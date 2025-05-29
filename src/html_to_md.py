import os
import html2text
from bs4 import BeautifulSoup
from tqdm import tqdm
import concurrent.futures
import config as cfg

# Directories to save markdown pages
os.makedirs(cfg.TXT_DIR, exist_ok=True)

def setup_html2text_converter():
    """
    Sets up and configures the html2text converter for clean markdown output.
    
    Returns:
        html2text.HTML2Text: Configured converter instance.
    """
    h = html2text.HTML2Text()
    
    # Configure for clean, standard markdown
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

def extract_dcterms_metadata(html_content):
    """
    Extracts DCTERMS metadata from HTML content.
    
    Args:
        html_content (str): HTML content to extract metadata from.
        
    Returns:
        dict: Dictionary containing DCTERMS metadata.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    metadata = {}
    
    # Extract DCTERMS metadata
    dcterms_identifier = soup.find('meta', attrs={'name': 'DCTERMS.identifier'})
    if dcterms_identifier:
        metadata['page_source'] = dcterms_identifier.get('content', '').strip()
    
    dcterms_title = soup.find('meta', attrs={'name': 'DCTERMS.title'})
    if dcterms_title:
        metadata['page_title'] = dcterms_title.get('content', '').strip()
    
    dcterms_modified = soup.find('meta', attrs={'name': 'DCTERMS.modified'})
    if dcterms_modified:
        metadata['page_modified'] = dcterms_modified.get('content', '').strip()
    
    dcterms_available = soup.find('meta', attrs={'name': 'DCTERMS.available'})
    if dcterms_available:
        metadata['page_available'] = dcterms_available.get('content', '').strip()
    
    return metadata

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

def clean_markdown(markdown_content):
    """
    Cleans up the markdown content by removing excessive whitespace.
    
    Args:
        markdown_content (str): Raw markdown content.
        
    Returns:
        str: Cleaned markdown content.
    """
    if not markdown_content:
        return ""
    
    # Split into lines and clean up
    lines = markdown_content.split('\n')
    cleaned_lines = []
    
    prev_empty = False
    for line in lines:
        stripped = line.rstrip()  # Keep leading spaces for indentation
        
        # Skip multiple consecutive empty lines
        if not stripped:
            if not prev_empty:
                cleaned_lines.append('')
            prev_empty = True
        else:
            cleaned_lines.append(stripped)
            prev_empty = False
    
    return '\n'.join(cleaned_lines).strip()

def create_frontmatter(metadata):
    """
    Creates YAML frontmatter with DCTERMS metadata.

    Args:
        metadata (dict): Dictionary containing DCTERMS metadata.

    Returns:
        str: YAML frontmatter block.
    """
    frontmatter_lines = ["---"]
    
    if 'page_source' in metadata:
        frontmatter_lines.append(f'page_source: "{metadata["page_source"]}"')
    
    if 'page_title' in metadata:
        frontmatter_lines.append(f'page_title: "{metadata["page_title"]}"')
    
    if 'page_modified' in metadata:
        frontmatter_lines.append(f'page_modified: "{metadata["page_modified"]}"')
    
    if 'page_available' in metadata:
        frontmatter_lines.append(f'page_available: "{metadata["page_available"]}"')
    
    frontmatter_lines.append("---")
    
    return "\n".join(frontmatter_lines)

def process_html_file(file_path, filename, converter):
    """
    Processes an HTML file to extract main content and convert it to Markdown.

    Args:
        file_path (str): Path to the HTML file.
        filename (str): Name of the HTML file.
        converter (html2text.HTML2Text): Configured converter instance.

    Returns:
        tuple: (markdown_content, metadata) - Processed Markdown content and extracted metadata.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        # Extract DCTERMS metadata from the full HTML
        metadata = extract_dcterms_metadata(html_content)
        
        # Extract main content
        main_html = extract_main_content(filename, html_content)
        if not main_html:
            return "", {}
        
        # Process links to make them absolute
        processed_html = process_links(main_html)
        
        # Convert to markdown
        markdown_content = converter.handle(processed_html)
        
        # Clean up the markdown
        cleaned_markdown = clean_markdown(markdown_content)
        
        return cleaned_markdown, metadata
        
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return "", {}

def load_html_content(directory, output_directory):
    """
    Loads HTML content from all files in the specified directory and saves as clean markdown.

    Args:
        directory (str): Path to the directory containing HTML files.
        output_directory (str): Path to the directory where output markdown files will be saved.

    Returns:
        None
    """
    # Set up the converter once
    converter = setup_html2text_converter()
    
    html_files = [f for f in os.listdir(directory) if f.endswith('.html')]
    
    for filename in tqdm(html_files, desc="Processing HTML files"):
        file_path = os.path.join(directory, filename)
        
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(process_html_file, file_path, filename, converter)
                processed_markdown, metadata = future.result(timeout=30)
            
            if processed_markdown:
                # Generate output filename
                base_name = os.path.splitext(filename)[0]
                output_file_path = os.path.join(output_directory, f"{base_name}.txt")
                
                with open(output_file_path, 'w', encoding='utf-8') as output_file:
                    # Write the YAML frontmatter with DCTERMS metadata
                    output_file.write(f"{create_frontmatter(metadata)}\n\n")
                    # Write the processed markdown content
                    output_file.write(processed_markdown)
            else:
                print(f"No content extracted from {filename}")
                
        except concurrent.futures.TimeoutError:
            print(f"Processing {filename} took too long and was skipped.")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

# Load and process HTML content
if __name__ == "__main__":
    load_html_content(cfg.HTML_DIR, cfg.TXT_DIR)