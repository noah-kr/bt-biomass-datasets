import os
import psycopg2
from shapely.geometry import Polygon
from shapely.wkt import loads as load_wkt
from osgeo import gdal, osr
from pyproj import CRS, Transformer


def reproject_geometry(input_geom, input_crs, target_crs):
    """Reproject geometry from input CRS to target CRS."""
    transformer = Transformer.from_crs(CRS.from_user_input(input_crs), CRS.from_user_input(target_crs), always_xy=True)
    transformed_coords = [transformer.transform(x, y) for x, y in input_geom.exterior.coords]
    return Polygon(transformed_coords)


def query_database(cursor, geom_wkt):
    """Query the database for intersecting TIFF files."""
    query = """
        SELECT tif_file_path, ST_AsText(location)
        FROM (
            SELECT tif_file_path, location FROM biomass_data
            UNION
            SELECT tif_file_path, location FROM canopy_height_data
        ) AS combined
        WHERE ST_Intersects(location, ST_GeomFromText(%s, 4326));
    """
    cursor.execute(query, (geom_wkt,))
    return cursor.fetchall()


def get_raster_geotransform(dataset):
    """Get the geotransform and CRS of the raster dataset."""
    geo_transform = dataset.GetGeoTransform()
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromWkt(dataset.GetProjection())
    return geo_transform, spatial_ref


def align_to_original_grid(value, origin, pixel_size, align_func):
    """Align a coordinate value to the original raster grid."""
    return origin + align_func((value - origin) / pixel_size) * pixel_size


def create_multi_layer_tif(intersecting_files, output_tif, input_geom, input_crs):
    """Create a multi-layer GeoTIFF with intersecting files."""
    driver = gdal.GetDriverByName("GTiff")
    first_ds = gdal.Open(intersecting_files[0])
    if not first_ds:
        raise FileNotFoundError(f"Could not open file: {intersecting_files[0]}")

    # Reproject input geometry to match the raster's CRS
    geo_transform, spatial_ref = get_raster_geotransform(first_ds)
    pixel_width = geo_transform[1]
    pixel_height = abs(geo_transform[5])
    origin_x = geo_transform[0]
    origin_y = geo_transform[3]

    raster_crs = spatial_ref.ExportToWkt()
    reprojected_geom = reproject_geometry(input_geom, input_crs, raster_crs)

    # Align bounds to the original raster grid
    bbox = reprojected_geom.bounds
    minx = align_to_original_grid(bbox[0], origin_x, pixel_width, round)
    maxx = align_to_original_grid(bbox[2], origin_x, pixel_width, round)
    miny = align_to_original_grid(bbox[1], origin_y, -pixel_height, round)
    maxy = align_to_original_grid(bbox[3], origin_y, -pixel_height, round)

    print(f"Aligned Geometry bounds: minx={minx}, miny={miny}, maxx={maxx}, maxy={maxy}")

    # Calculate raster dimensions
    cols = int((maxx - minx) / pixel_width)
    rows = int((maxy - miny) / pixel_height)

    print(f"Creating output dataset with rows={rows}, cols={cols}")

    # Enable LZW compression and BIGTIFF
    options = ["COMPRESS=LZW", "BIGTIFF=YES"]
    total_bands = sum(gdal.Open(f).RasterCount for f in intersecting_files)

    # Create the output dataset
    output_ds = driver.Create(output_tif, cols, rows, total_bands, first_ds.GetRasterBand(1).DataType, options)
    if output_ds is None:
        raise RuntimeError("Failed to create the output GeoTIFF dataset.")

    # Set geotransform and projection
    output_geotransform = (
        minx, pixel_width, 0,
        maxy, 0, -pixel_height
    )
    output_ds.SetGeoTransform(output_geotransform)
    output_ds.SetProjection(first_ds.GetProjection())

    band_offset = 0
    for intersecting_file in intersecting_files:
        print(f"Processing file: {intersecting_file}")
        src_ds = gdal.Open(intersecting_file)
        num_bands = src_ds.RasterCount
        for band_idx in range(1, num_bands + 1):
            clipped_ds = gdal.Warp(
                '', src_ds, format='MEM', outputBounds=(minx, miny, maxx, maxy),
                xRes=pixel_width, yRes=pixel_height, dstSRS=raster_crs,
                resampleAlg=gdal.GRA_NearestNeighbour
            )
            data = clipped_ds.GetRasterBand(band_idx).ReadAsArray()
            output_band = output_ds.GetRasterBand(band_offset + band_idx)
            output_band.WriteArray(data)
            band_offset += 1

    print(f"Created multi-layer GeoTIFF: {output_tif}")


def main():
    dbname = input("Enter the database name: ")
    user = input("Enter the database username: ")
    password = input("Enter the database password (leave blank if not set): ") or None
    host = input("Enter the database host (leave blank for default: localhost): ") or "localhost"
    port = input("Enter the database port (leave blank for default: 5432): ") or "5432"

    geom_wkt = input("Enter the geometry in WKT format: ")
    input_geom = load_wkt(geom_wkt)
    input_crs = input("Enter the CRS for the input geometry (default: EPSG:4326): ") or "EPSG:4326"
    output_dir = input("Enter the output directory for the multi-layer TIFF file: ")
    os.makedirs(output_dir, exist_ok=True)

    output_tif = os.path.join(output_dir, "intersected_data.tif")

    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    cursor = conn.cursor()

    results = query_database(cursor, geom_wkt)
    intersecting_files = [result[0] for result in results]

    create_multi_layer_tif(intersecting_files, output_tif, input_geom, input_crs)
    print("Processing completed.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
