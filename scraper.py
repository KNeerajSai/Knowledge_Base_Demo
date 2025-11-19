#!/usr/bin/env python3
"""
Healthcare Payer Knowledge Base - Web Scraper
Configurable web scraper to find and download provider manuals from healthcare payer websites.

This script crawls major healthcare payer websites to find and download policy manuals 
and clinical guidelines in PDF format, organizing them for database processing.

Author: Development Team
Date: November 2025
"""

import os
import requests
from bs4 import BeautifulSoup
import time
import logging
from urllib.parse import urljoin

# --- Configuration ---
# Configure logging to provide progress and error information.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Directory to save downloaded PDF files.
DOWNLOAD_DIR = 'payer_manuals'

# Headers to mimic a real web browser and avoid being blocked.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- Target Payers Configuration ---
# A list of dictionaries, each representing a target payer.
# 'name': The payer's name, used for creating subdirectories.
# 'search_url': The starting URL for finding provider manuals. This is often a search page or a resource library.
#
# NOTE: These URLs are starting points and may need to be updated if the websites change.
# For sites requiring logins or complex navigation, a more advanced tool like Selenium would be needed.
PAYERS = [
    {
        'name': 'UnitedHealthcare',
        'search_url': 'https://www.uhcprovider.com/en/policies-protocols.html'
    },
    {
        'name': 'Anthem',
        'search_url': 'https://www.anthem.com/provider/policies/clinical-guidelines'
    },
    {
        'name': 'Aetna',
        'search_url': 'https://www.aetna.com/health-care-professionals/clinical-practice-guidelines.html'
    },
    {
        'name': 'Humana',
        'search_url': 'https://www.humana.com/provider/medical-resources/medical-clinical-pharmacy-policies'
    },
    {
        'name': 'Centene_Ambetter_Wellcare',
        'search_url': 'https://www.ambetterhealth.com/provider-resources/manuals-and-guides.html'
    },
    {
        'name': 'Kaiser_Permanente',
        'search_url': 'https://providers.kp.org/'
    },
    {
        'name': 'Cigna',
        'search_url': 'https://www.cigna.com/healthcare-professionals'
    },
    {
        'name': 'Molina_Healthcare',
        'search_url': 'https://www.molinahealthcare.com/providers'
    }
]

def download_pdf(url, save_path):
    """
    Downloads a PDF file from a given URL and saves it to a specified path.

    Args:
        url (str): The URL of the PDF to download.
        save_path (str): The local file path to save the downloaded PDF.

    Returns:
        bool: True if download was successful, False otherwise.
    """
    try:
        logging.info(f"Downloading PDF from: {url}")
        response = requests.get(url, headers=HEADERS, stream=True, timeout=30)
        
        # Check if the request was successful and the content is a PDF.
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"Successfully saved PDF to: {save_path}")
            return True
        else:
            logging.error(f"Failed to download PDF. Status: {response.status_code}, Content-Type: {response.headers.get('Content-Type')}")
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while trying to download {url}: {e}")
        return False

def scrape_payer_site(payer_name, search_url):
    """
    Scrapes a payer's website to find and download PDF manuals.

    Args:
        payer_name (str): The name of the payer, for organizing downloads.
        search_url (str): The URL to start scraping from.
    """
    logging.info(f"--- Starting scrape for {payer_name} ---")
    
    # Create a dedicated directory for this payer's manuals.
    payer_dir = os.path.join(DOWNLOAD_DIR, payer_name)
    os.makedirs(payer_dir, exist_ok=True)
    
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            logging.error(f"Could not access {search_url}. Status code: {response.status_code}")
            return

        # Use BeautifulSoup to parse the HTML content of the page.
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all hyperlinks ('a' tags) on the page.
        links = soup.find_all('a', href=True)
        pdf_links_found = 0
        
        for link in links:
            href = link['href']
            # Check if the link ends with '.pdf'.
            if href.endswith('.pdf'):
                pdf_links_found += 1
                
                # Construct the full, absolute URL for the PDF.
                if href.startswith(('http://', 'https://')):
                    pdf_url = href
                else:
                    # Handle relative URLs by joining with the base search URL.
                    pdf_url = urljoin(search_url, href)

                # Create a clean filename from the URL.
                file_name = os.path.join(payer_dir, pdf_url.split('/')[-1])
                
                # Download the PDF if it doesn't already exist.
                if not os.path.exists(file_name):
                    download_pdf(pdf_url, file_name)
                    time.sleep(2)  # Be respectful and pause between downloads.
                else:
                    logging.info(f"PDF already exists, skipping: {file_name}")

        if pdf_links_found == 0:
            logging.warning(f"No direct PDF links found for {payer_name} on {search_url}. The site may use JavaScript to render links. Consider using Selenium for this target.")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while scraping {payer_name}: {e}")
    
    logging.info(f"--- Finished scrape for {payer_name} ---")

def main():
    """Main function to orchestrate the scraping process."""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        logging.info(f"Created download directory: {DOWNLOAD_DIR}")

    logging.info("Healthcare Payer Knowledge Base - Web Scraper")
    logging.info("=" * 50)
    
    for payer in PAYERS:
        scrape_payer_site(payer['name'], payer['search_url'])
        time.sleep(5)  # Pause between scraping different payers.
    
    logging.info("=" * 50)
    logging.info("Scraping completed. Check the 'payer_manuals' directory for downloaded PDFs.")

if __name__ == "__main__":
    main()