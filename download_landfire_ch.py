import os
import requests
from tqdm import tqdm

# Dictionary containing region names and their respective download URLs
LANDFIRE_URLS = {
    "Conus": "https://prod-is-usgs-sb-prod-content.s3.amazonaws.com/64f2465fd34e095955171e11/LF2022_CH_230_CONUS_20231026.zip?AWSAccessKeyId=AKIAI7K4IX6D4QLARINA&Expires=1732095111&Signature=ZMrYlDTeh8%2FZyEGC9hWmR7i2pdU%3D",
    "Alaska": "https://prod-is-usgs-sb-prod-content.s3.amazonaws.com/64f24e34d34e095955171e94/LF2022_CH_230_AK_20230530.zip?AWSAccessKeyId=AKIAI7K4IX6D4QLARINA&Expires=1732095192&Signature=K4AbVfaUoc6A1MQ86Df9cJc4Zak%3D",
    "Hawaii": "https://prod-is-usgs-sb-prod-content.s3.amazonaws.com/65665fead34e3aa43a43faae/LF2022_CH_230_HI_20231127.zip?AWSAccessKeyId=AKIAI7K4IX6D4QLARINA&Expires=1732095260&Signature=1IkJLmjNeYSVDyJ5nqr7YQVzn20%3D",
    "Puerto_Rico_Virgin_Islands": "https://prod-is-usgs-sb-prod-content.s3.amazonaws.com/655542f8d34ee4b6e05c463b/LF2022_CH_230_PRVI.zip?AWSAccessKeyId=AKIAI7K4IX6D4QLARINA&Expires=1732095290&Signature=8WH6mmejmSFVfTPKQZ8%2B6EPF%2BYY%3D",
}

# Function to download files with a progress bar
def download_file(url, target_directory, filename):
    file_path = os.path.join(target_directory, filename)
    
    # Skip download if file already exists
    if os.path.exists(file_path):
        print(f"{filename} already exists. Skipping.")
        return
    
    print(f"Downloading {filename}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Write file to disk with progress bar
        total_size = int(response.headers.get("content-length", 0))
        with open(file_path, "wb") as file, tqdm(
            desc=filename,
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as progress_bar:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
                progress_bar.update(len(chunk))
        print(f"{filename} downloaded successfully.")
    except requests.RequestException as e:
        print(f"Failed to download {filename}: {e}")

# Main function to handle downloading
def download_landfire_datasets():
    target_directory = input("Enter the directory where you want to save the LANDFIRE datasets: ").strip()
    os.makedirs(target_directory, exist_ok=True)
    
    for region, url in LANDFIRE_URLS.items():
        filename = f"{region}.zip"
        download_file(url, target_directory, filename)

# Execute the download
if __name__ == "__main__":
    download_landfire_datasets()
