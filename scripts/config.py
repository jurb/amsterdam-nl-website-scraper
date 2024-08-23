import os

BASE_DIR = '../data/'

HTML_DIR = os.path.join(BASE_DIR, 'html', 'scraped')
IMAGE_DIR = os.path.join(BASE_DIR, 'images', 'scraped')
TXT_DIR = os.path.join(BASE_DIR, 'txt', 'scraped')
FAILED_HTML_FILE = os.path.join(BASE_DIR, 'html', 'failed_html.txt')
FAILED_IMAGES_FILE = os.path.join(BASE_DIR, 'images', 'failed_images.txt')
