import os
import psycopg2
from shapely.geometry import Polygon
from shapely.wkt import loads as load_wkt
from osgeo import gdal, osr
from pyproj import CRS, Transformer
import math


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


def get_raster_crs(dataset):
    """Get the CRS of the raster dataset."""
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromWkt(dataset.GetProjection())
    return spatial_ref.ExportToWkt()


def create_multi_layer_tif(intersecting_files, output_tif, input_geom, input_crs):
    """Create a multi-layer GeoTIFF with intersecting files."""
    driver = gdal.GetDriverByName("GTiff")
    first_ds = gdal.Open(intersecting_files[0])
    if not first_ds:
        raise FileNotFoundError(f"Could not open file: {intersecting_files[0]}")

    # Reproject input geometry to match the raster's CRS
    raster_crs = get_raster_crs(first_ds)
    reprojected_geom = reproject_geometry(input_geom, input_crs, raster_crs)

    # Get input geometry bounds
    bbox = reprojected_geom.bounds
    geo_transform = first_ds.GetGeoTransform()
    pixel_width = geo_transform[1]
    pixel_height = abs(geo_transform[5])

    # Align bounds to the raster grid
    def align_to_grid(coord, offset, pixel_size, align_func):
        return offset + align_func((coord - offset) / pixel_size) * pixel_size

    minx = align_to_grid(bbox[0], geo_transform[0], pixel_width, math.floor)
    maxx = align_to_grid(bbox[2], geo_transform[0], pixel_width, math.ceil)
    miny = align_to_grid(bbox[1], geo_transform[3], -pixel_height, math.floor)
    maxy = align_to_grid(bbox[3], geo_transform[3], -pixel_height, math.ceil)

    print(f"Aligned Geometry bounds: minx={minx}, miny={miny}, maxx={maxx}, maxy={maxy}")

    # Calculate raster dimensions
    cols = int((maxx - minx) / pixel_width)
    rows = int((maxy - miny) / pixel_height)

    print(f"Calculated raster dimensions: cols={cols}, rows={rows}")

    # Enable LZW compression and BIGTIFF
    options = ["COMPRESS=LZW", "BIGTIFF=YES"]

    # Count total bands across all files
    total_bands = sum(gdal.Open(f).RasterCount for f in intersecting_files)
    print(f"Total number of bands: {total_bands}")

    # Create the output dataset
    output_ds = driver.Create(output_tif, cols, rows, total_bands, first_ds.GetRasterBand(1).DataType, options)
    if output_ds is None:
        raise RuntimeError("Failed to create the output GeoTIFF dataset.")

    # Set geotransform and projection
    output_geotransform = (
        minx,  # Top-left x
        pixel_width,  # Pixel width
        0,  # Rotation (x-axis)
        maxy,  # Top-left y
        0,  # Rotation (y-axis)
        -pixel_height  # Pixel height
    )
    output_ds.SetGeoTransform(output_geotransform)
    output_ds.SetProjection(first_ds.GetProjection())

    band_offset = 0
    for intersecting_file in intersecting_files:
        print(f"Processing file: {intersecting_file}")
        src_ds = gdal.Open(intersecting_file)
        if src_ds is None:
            print(f"Skipping {intersecting_file} as it could not be opened.")
            continue

        num_bands = src_ds.RasterCount
        filename = os.path.basename(intersecting_file)
        for band_idx in range(1, num_bands + 1):
            print(f"Processing band {band_idx} of {intersecting_file}")
            clipped_ds = gdal.Warp(
                '', src_ds, format='MEM', outputBounds=(minx, miny, maxx, maxy),
                dstSRS=raster_crs, xRes=pixel_width, yRes=pixel_height,
                resampleAlg=gdal.GRA_NearestNeighbour
            )

            if clipped_ds is None:
                print(f"Skipping band {band_idx} of {intersecting_file} as it does not intersect the geometry.")
                continue

            data = clipped_ds.GetRasterBand(band_idx).ReadAsArray()

            if data.shape != (rows, cols):
                print(f"Adjusting raster dimensions from {data.shape} to {(rows, cols)}.")
                data = data[:rows, :cols]  # Crop to expected dimensions

            output_band = output_ds.GetRasterBand(band_offset + band_idx)
            output_band.WriteArray(data)

            # Set band name to include the file name and band index
            band_name = f"{filename}_Band_{band_idx}"
            output_band.SetDescription(band_name)

        band_offset += num_bands

    output_ds = None
    print(f"Created multi-layer GeoTIFF: {output_tif}")


def main():
    dbname = input("Enter the database name: ")
    user = input("Enter the database username: ")
    password = input("Enter the database password (leave blank if not set): ") or None
    host = input("Enter the database host (leave blank for default: localhost): ") or "localhost"
    port = input("Enter the database port (leave blank for default: 5432): ") or "5432"

    geom_wkt = input("Enter the geometry in WKT format: ")
    try:
        input_geom = load_wkt(geom_wkt)
    except Exception as e:
        print(f"Error parsing WKT: {e}")
        return

    input_crs = input("Enter the CRS for the input geometry (default: EPSG:4326): ") or "EPSG:4326"
    output_dir = input("Enter the output directory for the multi-layer TIFF file: ")
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    output_tif = os.path.join(output_dir, "intersected_data.tif")

    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    cursor = conn.cursor()

    print(f"Input geometry (WKT): {input_geom.wkt}")

    reprojected_geom = reproject_geometry(input_geom, input_crs, "EPSG:4326")
    print(f"Reprojected geometry (WKT): {reprojected_geom.wkt}")

    results = query_database(cursor, reprojected_geom.wkt)
    if not results:
        print("No intersecting data found in the database.")
        return

    intersecting_files = [result[0] for result in results]

    create_multi_layer_tif(intersecting_files, output_tif, input_geom, input_crs)

    print("Processing completed.")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
