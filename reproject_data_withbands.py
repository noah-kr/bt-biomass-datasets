import os
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from multiprocessing import Pool, Manager, Lock
import time


def reproject_tif(input_output):
    """
    Reproject a single GeoTIFF file to the target CRS with LZW compression and BIGTIFF support,
    while preserving band names.
    
    Args:
        input_output (tuple): Contains input_path, output_path, target_crs, counter, total_tasks, lock.
    """
    input_path, output_path, target_crs, counter, total_tasks, lock = input_output
    
    if os.path.exists(output_path):
        with lock:
            counter.value += 1
            print(f"Skipped {counter.value}/{total_tasks}: {output_path} already exists.")
        return

    try:
        with rasterio.open(input_path) as src:
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds
            )
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': target_crs,
                'transform': transform,
                'width': width,
                'height': height,
                'compress': 'LZW',  # Add LZW compression
                'BIGTIFF': 'YES'    # Enable BigTIFF support
            })
            
            with rasterio.open(output_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    # Reproject the band data
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=Resampling.bilinear  # Bilinear resampling for continuous data
                    )
                    # Preserve the band description (name)
                    band_name = src.descriptions[i - 1]
                    if band_name:
                        dst.set_band_description(i, band_name)
        
        # Update the progress counter safely using the lock
        with lock:
            counter.value += 1
            print(f"Processed {counter.value}/{total_tasks}: {output_path}")
    
    except Exception as e:
        print(f"Error processing {input_path}: {e}")


def process_directory_parallel(base_dir, output_base_dir, target_crs="EPSG:4326", num_workers=4):
    """
    Reproject all .tif files in a directory structure to a target CRS in parallel with LZW compression.
    Skips files that are already processed and preserves band names.
    
    Args:
        base_dir (str): Path to the base directory containing GeoTIFF files.
        output_base_dir (str): Path to the base directory for reprojected and compressed files.
        target_crs (str): Target CRS in EPSG format.
        num_workers (int): Number of parallel processes to use.
    """
    tasks = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.tif') and not file.endswith('.aux.xml'):
                input_path = os.path.join(root, file)
                relative_path = os.path.relpath(root, base_dir)
                output_dir = os.path.join(output_base_dir, relative_path)
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, file)
                tasks.append((input_path, output_path, target_crs))
    
    total_tasks = len(tasks)
    print(f"Found {total_tasks} files to process. Starting with {num_workers} workers...")
    
    # Use a multiprocessing Manager to track progress
    with Manager() as manager:
        counter = manager.Value('i', 0)  # Shared counter
        lock = manager.Lock()  # Lock to ensure safe updates to the counter
        
        # Add counter, total_tasks, and lock to each task
        tasks = [(t[0], t[1], t[2], counter, total_tasks, lock) for t in tasks]
        
        # Process tasks in parallel
        with Pool(num_workers) as pool:
            pool.map(reproject_tif, tasks)
    
    print("Reprojection and compression completed successfully!")


if __name__ == "__main__":
    # Prompt the user for input and output directories
    base_dir = input("Enter the path to the input folder containing GeoTIFF files: ").strip()
    output_base_dir = input("Enter the path to the output folder for reprojected files: ").strip()
    target_crs = "EPSG:4326"  # Target CRS is hardcoded to WGS84

    # Check if the input directory exists
    if not os.path.exists(base_dir):
        print(f"Error: Input directory '{base_dir}' does not exist.")
        exit(1)
    
    # Ensure the output directory exists
    os.makedirs(output_base_dir, exist_ok=True)
    
    # Number of workers to use (adjust based on your system's resources)
    num_workers = 8
    
    # Reproject all files in parallel with progress tracking
    start_time = time.time()
    process_directory_parallel(base_dir, output_base_dir, target_crs, num_workers)
    end_time = time.time()

    print(f"Total processing time: {end_time - start_time:.2f} seconds")
