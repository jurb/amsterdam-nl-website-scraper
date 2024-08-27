import os
import re
from bs4 import BeautifulSoup
from tqdm import tqdm
import concurrent.futures
import config as cfg

# Directories to save txt pages
os.makedirs(cfg.TXT_DIR, exist_ok=True)

def extract_main_content_with_hrefs_and_api_dynamic(filename, html_content):
    """
    Extracts the main content from HTML, including handling images and API data,
    and processes text elements to replace hrefs dynamically.

    Args:
        filename (str): The name of the file being processed.
        html_content (str): The HTML content to be parsed.

    Returns:
        list: Processed text elements from the main content.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    main_content_selectors = [
        'div.content',
        'div.main-content',
        'article',
        '#main',
        '.article',
    ]

    main_content_container = get_main_content_container(soup, main_content_selectors)

    if main_content_container:
        text_list, href_dict = parse_main_content(main_content_container)
        return text_list, href_dict
    else:
        print("Relevant content not found for {}".format(filename))
        return [], {}

def get_main_content_container(soup, selectors):
    """
    Finds the main content container in the parsed HTML soup using provided selectors.

    Args:
        soup (BeautifulSoup): The parsed HTML content.
        selectors (list): List of CSS selectors to identify the main content.

    Returns:
        Tag or None: The first matching element found or None if no match is found.
    """
    return next((soup.select_one(selector) for selector in selectors if soup.select_one(selector)), None)

def handle_image_element(element):
    """
    Creates an HTML string for an image element.

    Args:
        element (Tag): The image tag.

    Returns:
        str: HTML string representation of the image tag.
    """
    src = element["src"]
    if "https" not in src:
        src = "https://www.amsterdam.nl" + src
    return "[IMG: {}]".format(src)

def input_hrefs(text_list, replacement_dict):
    """
    Replaces text with hrefs in the text list based on the replacement dictionary.

    Args:
        text_list (list): List of text elements.
        replacement_dict (dict): Dictionary with text as keys and href replacements as values.

    Returns:
        list: Updated list with hrefs replaced.
    """
    updated_list = []
    for text in text_list:
        for key, href in replacement_dict.items():
            if key in text:
                text = text.replace(key, href)
        updated_list.append(text)
    return updated_list

def clean_list(input_list):
    """
    Cleans the input list by removing markers.

    Args:
        input_list (list): List containing text elements.

    Returns:
        list: Cleaned list with markers removed.
    """
    updated_list = [item for item in input_list if item != "HEX"]
    updated_list = [item.replace("HEX", "") for item in updated_list]
    return [item.replace("WHITELINE", "") for item in updated_list]

def add_space_around_patterns(text_list):
    """
    Add spaces around specific patterns in a list of strings.
    
    This function processes a list of strings and adds spaces around 
    '[LINK: ...](...)' and '[IMG: ...]' patterns if they are concatenated 
    with other elements. It also removes extra spaces if already present.

    Args:
        text_list (list of str): List of strings to be processed.

    Returns:
        list of str: List of processed strings with spaces added around specified patterns.
    """
    link_pattern = re.compile(r'(\[LINK:[^\]]+\]\([^\)]+\))')
    img_pattern = re.compile(r'(\[IMG:[^\]]+\])')
    modified_text_list = []
    for text in text_list:
        modified_text = re.sub(link_pattern, r' \1 ', text)
        modified_text = re.sub(img_pattern, r' \1 ', modified_text)
        modified_text = re.sub(r'\s+', ' ', modified_text)
        modified_text_list.append(modified_text.strip())
    return modified_text_list

def parse_main_content(container):
    """
    Parses the main content container to extract text and handle various elements.

    Args:
        container (Tag): The main content container element.

    Returns:
        tuple: A tuple containing the text list and href dictionary.
    """
    text_list = []
    href_dict = {}
    prev_element = ""

    for element in container.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'a', 'ol', 'ul']):
        to_add = None
        cur_element = element.name

        if element.name == 'a' and element.get('href'):
            text = element.get_text(strip=True)
            addition = "[LINK: {}]({})".format(text, element["href"])
            if text:
                href_dict[text] = addition
            else:
                to_add = addition

        elif element.name == 'div' and element.has_attr('data-keys') and element.has_attr('data-config'):
            data_keys = element.get('data-keys')
            data_config = element.get('data-config')
            to_add = f'\nAPI Information:\ndata-keys: {data_keys}\ndata-config: {data_config}\n'

        elif element.name == 'p' and element.find('img'):
            text = element.get_text(strip=True)
            if text:
                text_list.append(text)
            img_element = element.find('img')
            to_add = handle_image_element(img_element)

        else:
            to_add = element.get_text(strip=True)
            if to_add:
                text_list = [item.replace(to_add, "HEX") if to_add in item else item for item in text_list]

        if to_add:
            if any(
                (prefix in prev_element and "h" in cur_element)
                for prefix in ["h", "p", "a", "li"]
            ):
                text_list.append("WHITELINE")
            text_list.append(to_add)
        prev_element = cur_element

    return text_list, href_dict

def process_html_file(file_path, filename):
    """
    Processes an HTML file to extract main content and save it to a text file.

    Args:
        file_path (str): Path to the HTML file.
        filename (str): Name of the HTML file.

    Returns:
        list: Processed text elements from the main content.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    processed_text, href_dict = extract_main_content_with_hrefs_and_api_dynamic(filename, html_content)
    if processed_text:
        processed_text = clean_list(processed_text)
        processed_text = input_hrefs(processed_text, href_dict)
        processed_text = add_space_around_patterns(processed_text)
    return processed_text

def transform_string(input_string):
    """
    Transforms an input string into a formatted markdown link.

    Args:
        input_string (str): The input string with hyphens and underscores, ending with an underscore.

    Returns:
        str: The formatted markdown link.
    
    Example:
        >>> transform_string("onderwijs-jeugd_schooltuinen-natuureducatie_broekhuijsen_")
        '[PAGE LINK: onderwijs ... broekhuijsen](https://www.amsterdam.nl/onderwijs/.../broekhuijsen/)'
    """
    # Remove the trailing underscore
    input_string = input_string.rstrip('_')

    # Replace hyphens and underscores with spaces for the page link text
    page_link_text = input_string.replace('-', ' ').replace('_', ' ')

    # Replace underscores with forward slashes for the URL path
    url_path = input_string.replace('_', '/')

    # Construct the markdown link
    markdown_link = f"[PAGE LINK: {page_link_text}](https://www.amsterdam.nl/{url_path}/)"

    return markdown_link

def load_html_content(directory, output_directory):
    """
    Loads HTML content from all files in the specified directory and saves processed text to output directory.

    Args:
        directory (str): Path to the directory containing HTML files.
        output_directory (str): Path to the directory where output text files will be saved.

    Returns:
        None
    """
    for filename in tqdm(os.listdir(directory), desc="Processing HTML files"):
        if filename.endswith('.html'):
            file_path = os.path.join(directory, filename)
            try:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(process_html_file, file_path, filename)
                    processed_text = future.result(timeout=10)
                
                output_file_path = os.path.join(output_directory, f"{os.path.splitext(filename)[0]}.txt")
                with open(output_file_path, 'w', encoding='utf-8') as output_file:
                    output_file.write('{}\n\n'.format(transform_string(os.path.splitext(filename)[0])))
                    output_file.write('\n'.join(processed_text))
                
            except concurrent.futures.TimeoutError:
                print(f"Processing {filename} took too long and was skipped.")

# Load and process HTML content
load_html_content(cfg.HTML_DIR, cfg.TXT_DIR)