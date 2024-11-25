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
    """Reprojects a polygon from its source CRS to EPSG:4326."""
    src_crs = osr.SpatialReference()
    src_crs.ImportFromWkt(src_wkt)
    proj4 = src_crs.ExportToProj4()
    
    if not proj4:
        raise ValueError("Invalid source CRS: Could not determine projection.")
    
    transformer = Transformer.from_crs(proj4, 'EPSG:4326', always_xy=True)
    return transform(transformer.transform, polygon)

# Function to insert GeoTIFF data into the database
def insert_geotiff_data(cursor, file_path, source, acquisition_year, table_name):
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

        # Transform polygon if needed
        polygon_4326 = get_polygon_in_4326(polygon, src_wkt)

        # Insert the data into the specified table
        insert_query = f"""
        INSERT INTO {table_name} (location, source, acquisition_date, tif_file_path)
        VALUES (ST_GeomFromText(%s, 4326), %s, %s, %s)
        """
        acquisition_date = f"{acquisition_year}-01-01"
        cursor.execute(insert_query, (polygon_4326.wkt, source, acquisition_date, file_path))
        print(f"Inserted {file_path} into {table_name} from {source}")
        
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")

# Main function
def main():
    # Get database connection details
    dbname = input("Enter the database name: ")
    user = input("Enter the database username: ")
    password = input("Enter the database password (leave blank if not set): ") or None
    host = input("Enter the database host (default: localhost): ") or "localhost"
    port = input("Enter the database port (default: 5432): ") or "5432"

    # Get data location
    folder_path = input("Enter the folder containing GeoTIFF files: ")

    # Validate data root
    if not os.path.isdir(folder_path):
        print(f"Folder {folder_path} does not exist.")
        return

    # Get table name
    table_name = input("Enter the target table (biomass_data or canopy_height_data): ").strip()
    if table_name not in ['biomass_data', 'canopy_height_data']:
        print("Invalid table name. Please enter 'biomass_data' or 'canopy_height_data'.")
        return

    # Get source and acquisition year
    source = input("Enter the source name: ")
    acquisition_year = input("Enter the acquisition year (e.g., 2021): ")

    # Connect to the database
    conn = connect_to_db(dbname, user, password, host, port)
    if not conn:
        return
    cursor = conn.cursor()

    # Process each GeoTIFF file in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith('.tif'):
            file_path = os.path.join(folder_path, filename)
            insert_geotiff_data(cursor, file_path, source, acquisition_year, table_name)

    # Commit changes and close connection
    conn.commit()
    cursor.close()
    conn.close()
    print("Data loading completed.")

if __name__ == '__main__':
    main()
