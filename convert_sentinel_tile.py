import os
import geopandas as gpd
import sys
import shapely.ops 

def load_shapefile(shapefile_dir):
    """
    Load the Sentinel-2 shapefile index from the specified directory.

    Args:
        shapefile_dir (str): The directory containing the shapefile.

    Returns:
        gpd.GeoDataFrame: The GeoDataFrame loaded from the shapefile.
    """
    for file in os.listdir(shapefile_dir):
        if file.endswith(".shp") and "centroid" not in file:  # Exclude centroid shapefile since we want polygons and not points
            shapefile_path = os.path.join(shapefile_dir, file)
            try:
                print(f"Loading shapefile: {shapefile_path}")
                gdf = gpd.read_file(shapefile_path)
                return gdf
            except Exception as e:
                print(f"Error loading shapefile: {e}")
                sys.exit(1)

    print("No valid .shp file found in the specified directory.")
    sys.exit(1)

def get_tile_geometry(gdf, tile_name):
    """
    Retrieve the 2D geometry in WKT format for a specified Sentinel-2 tile.

    Args:
        gdf (gpd.GeoDataFrame): The GeoDataFrame containing Sentinel-2 tiles.
        tile_name (str): The name of the Sentinel-2 tile to retrieve.

    Returns:
        str: The 2D geometry in WKT format.
    """
    tile_row = gdf[gdf['Name'] == tile_name]
    if tile_row.empty:
        print(f"Tile {tile_name} not found in the shapefile.")
        sys.exit(1)

    geometry = tile_row.iloc[0].geometry

    # Ensure the geometry is a polygon and drop Z values if present
    if geometry.is_empty:
        print(f"No geometry found for tile {tile_name}.")
        sys.exit(1)

    if geometry.has_z:
        geometry = shapely.ops.transform(lambda x, y, z=None: (x, y), geometry)

    return geometry.wkt  # get the WKT representation

def main():
    shapefile_dir = input("Enter the directory containing the Sentinel-2 shapefile index: ").strip()
    if not os.path.isdir(shapefile_dir):
        print(f"The specified directory does not exist: {shapefile_dir}")
        sys.exit(1)

    tile_name = input("Enter the Sentinel-2 tile name (e.g., '04QFJ'): ").strip()
    gdf = load_shapefile(shapefile_dir)
    wkt_geometry = get_tile_geometry(gdf, tile_name)

    print(f"WKT Geometry for tile {tile_name}:")
    print(wkt_geometry)

if __name__ == "__main__":
    main()
