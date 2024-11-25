import os
import requests

# Ask the user for the base directory
BASE_DIR = input("Enter the directory where you want to save the dataset: ").strip()

# Ensure base directory exists
os.makedirs(BASE_DIR, exist_ok=True)
print(f"Using base directory: {BASE_DIR}")

# File containing the list of URLs
LINKS_FILE = "china_AGB_links.txt"

# Read the list of URLs
with open(LINKS_FILE, "r") as file:
    urls = file.readlines()

# Function to download and save each file
def download_file(url):
    year = url.split("/V1/")[1][:4]  # Extract year from the URL
    year_dir = os.path.join(BASE_DIR, year)
    os.makedirs(year_dir, exist_ok=True)
    
    filename = url.split("fileName=")[1]  # Extract filename from URL
    filepath = os.path.join(year_dir, filename)
    
    if os.path.exists(filepath):
        print(f"{filename} already exists. Skipping download.")
        return
    
    print(f"Downloading {filename} to {year_dir}")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded {filename}")
    except requests.RequestException as e:
        print(f"Failed to download {filename}: {e}")

# Download each file
for url in urls:
    download_file(url.strip())
