import psycopg2

# Function to establish a connection to the PostgreSQL database
def connect_to_db():
    try:
        dbname = input("Enter the database name: ")
        user = input("Enter the database username: ")
        password = input("Enter the database password (leave blank if not set): ") or None
        host = input("Enter the database host (leave blank for default: localhost): ") or "localhost"
        port = input("Enter the database port (leave blank for default: 5432): ") or "5432"

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

# Main function to query for TIFF files based on latitude and longitude
def main():
    conn = connect_to_db()
    if not conn:
        return
    
    cursor = conn.cursor()

    # Get latitude and longitude from the user
    try:
        latitude = float(input("Enter the latitude: "))
        longitude = float(input("Enter the longitude: "))
    except ValueError:
        print("Invalid input. Please enter numeric values for latitude and longitude.")
        cursor.close()
        conn.close()
        return

    # Query for TIFF files in biomass_data table
    query_biomass = """
    SELECT 'biomass_data' AS table_name, tif_file_path
    FROM biomass_data
    WHERE ST_Intersects(
        location,
        ST_SetSRID(ST_Point(%s, %s), 4326)::GEOGRAPHY
    );
    """

    # Query for TIFF files in canopy_height_data table
    query_canopy = """
    SELECT 'canopy_height_data' AS table_name, tif_file_path
    FROM canopy_height_data
    WHERE ST_Intersects(
        location,
        ST_SetSRID(ST_Point(%s, %s), 4326)::GEOGRAPHY
    );
    """

    # Execute both queries
    cursor.execute(query_biomass, (longitude, latitude))
    biomass_results = cursor.fetchall()

    cursor.execute(query_canopy, (longitude, latitude))
    canopy_results = cursor.fetchall()

    # Combine results
    results = biomass_results + canopy_results

    # Print the results
    if results:
        print("TIFF file paths containing the specified point:")
        for row in results:
            print(f"Table: {row[0]}, TIFF file path: {row[1]}")
    else:
        print("No TIFF files found for the specified point in either table.")

    # Close connection
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
