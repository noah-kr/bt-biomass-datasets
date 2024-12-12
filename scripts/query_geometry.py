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


def get_finest_resolution(intersecting_files):
    """Find the finest resolution among all intersecting files."""
    min_pixel_width = float('inf')
    min_pixel_height = float('inf')

    for intersecting_file in intersecting_files:
        ds = gdal.Open(intersecting_file)
        geo_transform, _ = get_raster_geotransform(ds)
        min_pixel_width = min(min_pixel_width, geo_transform[1])
        min_pixel_height = min(min_pixel_height, abs(geo_transform[5]))
        ds = None 

    return min_pixel_width, min_pixel_height


def create_multi_layer_tif(intersecting_files, output_tif, input_geom, input_crs, resolution=None, target_crs="EPSG:4326"):
    """Create a multi-layer GeoTIFF with intersecting files."""
    if resolution is None:
        resolution_x, resolution_y = get_finest_resolution(intersecting_files)
    else:
        resolution_x = resolution_y = resolution

    driver = gdal.GetDriverByName("GTiff")
    first_ds = gdal.Open(intersecting_files[0])
    if not first_ds:
        raise FileNotFoundError(f"Could not open file: {intersecting_files[0]}")

    geo_transform, spatial_ref = get_raster_geotransform(first_ds)
    origin_x = geo_transform[0]
    origin_y = geo_transform[3]

    raster_crs = spatial_ref.ExportToWkt()
    reprojected_geom = reproject_geometry(input_geom, input_crs, raster_crs)

    bbox = reprojected_geom.bounds
    minx = align_to_original_grid(bbox[0], origin_x, resolution_x, round)
    maxx = align_to_original_grid(bbox[2], origin_x, resolution_x, round)
    miny = align_to_original_grid(bbox[1], origin_y, -resolution_y, round)
    maxy = align_to_original_grid(bbox[3], origin_y, -resolution_y, round)

    cols = int(round((maxx - minx) / resolution_x))
    rows = int(round((maxy - miny) / resolution_y))

    maxx = minx + cols * resolution_x
    maxy = miny + rows * resolution_y

    if cols <= 0 or rows <= 0:
        raise ValueError("Calculated dimensions are zero or negative. Check input geometry and alignment.")

    print(f"Using resolution: {resolution_x} x {resolution_y}")
    print(f"Aligned bounds: minx={minx}, maxx={maxx}, miny={miny}, maxy={maxy}")
    print(f"Calculated dimensions: cols={cols}, rows={rows}")

    options = ["COMPRESS=LZW", "BIGTIFF=YES"]
    total_bands = sum(gdal.Open(f).RasterCount for f in intersecting_files)

    output_ds = driver.Create(output_tif, cols, rows, total_bands, first_ds.GetRasterBand(1).DataType, options)
    if output_ds is None:
        raise RuntimeError("Failed to create the output GeoTIFF dataset.")

    output_geotransform = (minx, resolution_x, 0, maxy, 0, -resolution_y)
    output_ds.SetGeoTransform(output_geotransform)
    output_ds.SetProjection(raster_crs)

    band_offset = 0
    for intersecting_file in intersecting_files:
        src_ds = gdal.Open(intersecting_file)
        num_bands = src_ds.RasterCount
        for band_idx in range(1, num_bands + 1):
            clipped_ds = gdal.Warp(
                '', src_ds, format='MEM', outputBounds=(minx, miny, maxx, maxy),
                xRes=resolution_x, yRes=resolution_y, dstSRS=raster_crs,
                resampleAlg=gdal.GRA_NearestNeighbour
            )
            data = clipped_ds.GetRasterBand(band_idx).ReadAsArray()

            if data.shape != (rows, cols):
                raise ValueError(
                    f"Array shape {data.shape} does not match output dimensions ({rows}, {cols})."
                )

            output_band = output_ds.GetRasterBand(band_offset + band_idx)
            output_band.WriteArray(data)

            # Name the band based on source file and band index
            output_band.SetDescription(f"Source: {os.path.basename(intersecting_file)}, Band: {band_idx}")
        band_offset += num_bands

    print(f"Created multi-layer GeoTIFF: {output_tif}")

    if target_crs != "EPSG:4326":
        print(f"Reprojecting output to {target_crs}...")
        reprojected_tif = output_tif.replace(".tif", f"_{target_crs.replace(':', '_')}.tif")
        gdal.Warp(
            reprojected_tif,
            output_tif,
            dstSRS=target_crs,
            format="GTiff",
            creationOptions=["COMPRESS=LZW", "BIGTIFF=YES"]
        )
        print(f"Reprojected output saved to {reprojected_tif}")


def main():
    dbname = input("Enter the database name: ") or "bmdata"
    user = input("Enter the database username: ") or "nkreyenkamp"
    password = input("Enter the database password (leave blank if not set): ") or None
    host = input("Enter the database host (leave blank for default: localhost): ") or "localhost"
    port = input("Enter the database port (leave blank for default: 5432): ") or "5432"

    geom_wkt = input("Enter the geometry in WKT format: ")
    input_geom = load_wkt(geom_wkt)
    input_crs = input("Enter the CRS for the input geometry (default: EPSG:4326): ") or "EPSG:4326"
    output_dir = input("Enter the output directory for the multi-layer TIFF file: ")
    os.makedirs(output_dir, exist_ok=True)

    output_tif = os.path.join(output_dir, "intersected_data.tif")
    resolution_input = input("Enter the desired spatial resolution in meters (leave blank for original resolution): ")
    resolution = float(resolution_input) / 111320.0 if resolution_input else None
    target_crs = input("Enter the CRS for the output file (default: EPSG:4326): ") or "EPSG:4326"

    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    cursor = conn.cursor()

    results = query_database(cursor, geom_wkt)
    intersecting_files = [result[0] for result in results]

    if intersecting_files:
        print("The following intersecting files were found:")
        for file_path in intersecting_files:
            print(f" - {file_path}")
    else:
        print("No intersecting files found. Exiting.")
        cursor.close()
        conn.close()
        return

    create_multi_layer_tif(intersecting_files, output_tif, input_geom, input_crs, resolution, target_crs)
    print("Processing completed.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
