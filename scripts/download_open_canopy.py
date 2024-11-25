from huggingface_hub import snapshot_download
from tqdm import tqdm
import os
import shutil

# Ask the user for the target directory
target_directory = input("Enter the directory where you want to save the dataset: ").strip()

# Create target directory if it doesn't exist
if not os.path.isdir(target_directory):
    os.makedirs(target_directory)
    print(f"Created target directory: {target_directory}")
else:
    print(f"Using existing target directory: {target_directory}")

# Download function with tqdm progress bar
def download_with_progress(repo_id, local_dir, resume_download=True):
    # Temporarily download to a staging directory
    temp_dir = f"{local_dir}_staging"
    if not os.path.isdir(temp_dir):
        os.makedirs(temp_dir)
    
    print("Starting download with progress tracking...")
    
    # Start the download
    downloaded_files = snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        local_dir=temp_dir,
        resume_download=resume_download,
    )
    
    # Moving files and showing progress with tqdm
    with tqdm(total=len(downloaded_files), desc="Downloading files", unit="file") as pbar:
        for file in downloaded_files:
            relative_path = os.path.relpath(file, temp_dir)
            target_path = os.path.join(local_dir, relative_path)
            target_dir = os.path.dirname(target_path)
            
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            
            shutil.move(file, target_path)
            pbar.update(1)

    # Clean up staging directory
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)

# Download the dataset with progress tracking and resume capability
download_with_progress(
    repo_id="AI4Forest/Open-Canopy",
    local_dir=target_directory,
    resume_download=True,
)

print(f"Dataset downloaded to {target_directory}")
