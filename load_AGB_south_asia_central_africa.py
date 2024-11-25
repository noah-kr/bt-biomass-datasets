import os
import psycopg2
from osgeo import gdal, osr
from shapely.geometry import Polygon
from shapely.ops import transform
from pyproj import CRS, Transformer

# Function to establish a connection to the PostgreSQL database
def connect_to_db(dbname, user, password, host, port):
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

# Function to determine CRS and transform if needed
def get_polygon_in_4326(polygon, src_wkt):
    """Reproject a polygon to EPSG:4326 using its source WKT."""
    src_crs = osr.SpatialReference()
    src_crs.ImportFromWkt(src_wkt)
    proj4 = src_crs.ExportToProj4()
    
    if not proj4:
        raise ValueError("Invalid source CRS: Could not determine projection.")
    
    transformer = Transformer.from_crs(proj4, 'EPSG:4326', always_xy=True)
    return transform(transformer.transform, polygon)

# Function to insert GeoTIFF data into the database
def insert_geotiff_data(cursor, file_path, source):
    try:
        # Open the GeoTIFF file
        dataset = gdal.Open(file_path)
        if dataset is None:
            print(f"Could not open {file_path}")
            return

        # Get GeoTIFF coordinates
        geo_transform = dataset.GetGeoTransform()
        width = dataset.RasterXSize
        height = dataset.RasterYSize

        # Calculate the corner coordinates of the raster
        min_x = geo_transform[0]
        max_y = geo_transform[3]
        max_x = min_x + geo_transform[1] * width
        min_y = max_y + geo_transform[5] * height

        # Create a Polygon from the coordinates
        polygon = Polygon([(min_x, min_y), (min_x, max_y), (max_x, max_y), (max_x, min_y), (min_x, min_y)])

        # Check the CRS of the GeoTIFF file
        src_wkt = dataset.GetProjection()
        if not src_wkt:
            print(f"No CRS information found in {file_path}")
            return

        # Transform polygon to EPSG:4326 if needed
        polygon_4326 = get_polygon_in_4326(polygon, src_wkt)

        # Insert the data into the database with fixed acquisition date "2023-01-01"
        insert_query = """
        INSERT INTO biomass_data (location, source, acquisition_date, tif_file_path)
        VALUES (ST_GeomFromText(%s, 4326), %s, %s, %s)
        """
        acquisition_date = "2023-01-01"
        cursor.execute(insert_query, (polygon_4326.wkt, source, acquisition_date, file_path))
        print(f"Inserted {file_path} from {source}")
        
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")

# Main function to process the predefined folders
def main():
    # Get database connection details
    dbname = input("Enter the database name: ")
    user = input("Enter the database username: ")
    password = input("Enter the database password (leave blank if not set): ") or None
    host = input("Enter the database host (leave blank for default: localhost): ") or "localhost"
    port = input("Enter the database port (leave blank for default: 5432): ") or "5432"

    # Get root folder
    root_folder = input("Enter the root folder containing LiDAR data: ")
    if not os.path.isdir(root_folder):
        print(f"Folder {root_folder} does not exist.")
        return

    # Define the subfolders to process
    subfolders = {
        "LiDAR-based_biomass_maps_Central_Africa": os.path.join(root_folder, "LiDAR-based_biomass_maps_Central_Africa"),
        "LiDAR-based_biomass_maps_South_Asia": os.path.join(root_folder, "LiDAR-based_biomass_maps_South_Asia")
    }

    # Validate subfolder paths
    for name, path in subfolders.items():
        if not os.path.isdir(path):
            print(f"Subfolder {path} does not exist. Please ensure the folder structure is correct.")
            return

    # Connect to the database
    conn = connect_to_db(dbname, user, password, host, port)
    if not conn:
        return
    cursor = conn.cursor()

    # Process each source folder
    for source, folder_path in subfolders.items():
        print(f"Processing folder: {folder_path}")

        # Loop through files in each folder
        for filename in os.listdir(folder_path):
            if filename.endswith('.tif'):
                file_path = os.path.join(folder_path, filename)
                insert_geotiff_data(cursor, file_path, source)

    # Commit changes and close connection
    conn.commit()
    cursor.close()
    conn.close()
    print("Data loading completed.")

if __name__ == '__main__':
    main()
