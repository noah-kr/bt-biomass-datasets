import os
import psycopg2
from osgeo import gdal, osr
from shapely.geometry import Polygon
from shapely.ops import transform
from pyproj import Transformer

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
def get_polygon_in_4326(polygon, src_crs):
    if src_crs != 'EPSG:4326':
        transformer = Transformer.from_crs(src_crs, 'EPSG:4326', always_xy=True)
        return transform(transformer.transform, polygon)
    return polygon

# Function to insert GeoTIFF data into the canopy_height_data table
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
        proj_info = osr.SpatialReference()
        proj_info.ImportFromWkt(dataset.GetProjection())
        src_crs = proj_info.GetAttrValue("AUTHORITY", 0) + ":" + proj_info.GetAttrValue("AUTHORITY", 1)

        # Transform polygon if needed
        polygon_4326 = get_polygon_in_4326(polygon, src_crs)

        # Insert the data into the database with acquisition date "2022-01-01"
        insert_query = """
        INSERT INTO canopy_height_data (location, source, acquisition_date, tif_file_path)
        VALUES (ST_GeomFromText(%s, 4326), %s, %s, %s)
        """
        acquisition_date = "2022-01-01"
        cursor.execute(insert_query, (polygon_4326.wkt, source, acquisition_date, file_path))
        print(f"Inserted {file_path} from {source}")
        
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")

# Main function to process user-specified LANDFIRE root folder
def main():
    # Get database connection details
    dbname = input("Enter the database name: ")
    user = input("Enter the database username: ")
    password = input("Enter the database password (leave blank if not set): ") or None
    host = input("Enter the database host (default: localhost): ") or "localhost"
    port = input("Enter the database port (default: 5432): ") or "5432"

    # Get LANDFIRE root folder
    root_folder = input("Enter the root folder containing LANDFIRE data: ")
    if not os.path.isdir(root_folder):
        print(f"Folder {root_folder} does not exist.")
        return

    # Connect to the database
    conn = connect_to_db(dbname, user, password, host, port)
    if not conn:
        return
    cursor = conn.cursor()

    # Process each subdirectory in the LANDFIRE root folder
    for region_folder in os.listdir(root_folder):
        region_path = os.path.join(root_folder, region_folder, 'Tif')
        if os.path.isdir(region_path):
            print(f"Processing folder: {region_path}")

            # Loop through files in each Tif folder
            for filename in os.listdir(region_path):
                if filename.endswith('.tif'):
                    file_path = os.path.join(region_path, filename)
                    insert_geotiff_data(cursor, file_path, region_folder)

    # Commit changes and close connection
    conn.commit()
    cursor.close()
    conn.close()
    print("Data loading completed.")

if __name__ == '__main__':
    main()
