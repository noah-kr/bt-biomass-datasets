from huggingface_hub import snapshot_download
import os

# Ask the user for the target directory
target_directory = input("Enter the directory where you want to save the dataset: ").strip()

# Create target directory if it doesn't exist
if not os.path.isdir(target_directory):
    os.makedirs(target_directory)
    print(f"Created target directory: {target_directory}")
else:
    print(f"Using existing target directory: {target_directory}")

# Define the allowed patterns to include only lidar directories
allowed_patterns = [
    "canopy_height/*/lidar/**"  # Matches all files inside lidar directories
]

# Download function with filtering at the source
def download_with_filter(repo_id, local_dir):
    print("Starting filtered download...")
    # Download only files matching the allowed patterns
    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        local_dir=local_dir,
        allow_patterns=allowed_patterns,
        resume_download=True,
    )
    print(f"Filtered dataset downloaded to {local_dir}")

# Download the dataset with filtering
download_with_filter(
    repo_id="AI4Forest/Open-Canopy",
    local_dir=target_directory,
)

print(f"Dataset downloaded to {target_directory}")
