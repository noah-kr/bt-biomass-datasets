import psycopg2
from psycopg2 import sql

# SQL commands to create the schema
SCHEMA_SQL = """
-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create biomass_data table
CREATE TABLE IF NOT EXISTS biomass_data (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(POLYGON, 4326) NOT NULL,
    source VARCHAR(255) NOT NULL,
    acquisition_date DATE NOT NULL,
    tif_file_path TEXT NOT NULL
);

-- Create canopy_height_data table
CREATE TABLE IF NOT EXISTS canopy_height_data (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(POLYGON, 4326) NOT NULL,
    source VARCHAR(255) NOT NULL,
    acquisition_date DATE NOT NULL,
    tif_file_path TEXT NOT NULL
);

-- Create spatial indexes
CREATE INDEX IF NOT EXISTS idx_biomass_data_location
    ON biomass_data USING GIST(location);

CREATE INDEX IF NOT EXISTS idx_canopy_height_data_location
    ON canopy_height_data USING GIST(location);
"""

def get_db_config():
    """Prompt the user for database connection parameters."""
    dbname = input("Enter the default database name to connect to (leave blank for default: postgres): ") or "postgres"
    user = input("Enter the database username: ")
    password = input("Enter the database password (leave blank if not set): ") or None
    host = input("Enter the database host (leave blank for default: localhost): ") or "localhost"
    port = input("Enter the database port (leave blank for default: 5432): ") or "5432"

    return {
        "dbname": dbname,
        "user": user,
        "password": password,
        "host": host,
        "port": port
    }

def create_database(config, target_db):
    """Create the target database."""
    try:
        # Connect to the default PostgreSQL database
        conn = psycopg2.connect(**config)
        conn.autocommit = True
        cursor = conn.cursor()

        # Check if the database already exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
        if cursor.fetchone():
            print(f"Database '{target_db}' already exists.")
        else:
            # Create the new database
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_db)))
            print(f"Database '{target_db}' created successfully.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")

def apply_schema(config, target_db):
    """Apply the schema to the target database."""
    try:
        # Update config to connect to the target database
        db_config = config.copy()
        db_config["dbname"] = target_db

        # Connect to the target database
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Execute the schema SQL commands
        cursor.execute(SCHEMA_SQL)
        print(f"Schema applied successfully to the database '{target_db}'.")
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error applying schema: {e}")

if __name__ == "__main__":
    # Step 1: Get database connection details
    db_config = get_db_config()
    
    # Step 2: Prompt for the target database name
    target_db = input("Enter the target database name to create: ")

    # Step 3: Create the database
    create_database(db_config, target_db)

    # Step 4: Apply the schema
    apply_schema(db_config, target_db)
