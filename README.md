# Biomass and Canopy Height Database
This repository provides the scripts and instructions to set up, download, process, and query a database for above-ground biomass (AGB) and canopy height data, combining various datasets.

**Author**: Noah Kreyenkamp

## Overview

This repository provides a streamlined solution to work with geospatial data related to biomass and canopy height. The database integrates datasets from:

- **[Open-Canopy Dataset (France)](https://github.com/fajwel/Open-Canopy/tree/main)**
- **[AGB Dataset (China)](https://www.scidb.cn/en/detail?dataSetId=f48c4983dbd84a4c9c287111ac91c5aa)**
- **[LiDAR-based AGB Dataset (South Asia and Central Africa)](https://dataverse.ird.fr/dataset.xhtml?persistentId=doi:10.23708/H2MHXF)**
- **LANDFIRE 2022 Canopy Height Dataset ([Conus](https://www.sciencebase.gov/catalog/item/64f2465fd34e095955171e11), [Alaska](https://www.sciencebase.gov/catalog/item/64f24e34d34e095955171e94), [Hawaii](https://www.sciencebase.gov/catalog/item/65665fead34e3aa43a43faae), [Puerto Rico](https://www.sciencebase.gov/catalog/item/655542f8d34ee4b6e05c463b))**

The repository contains scripts to:

- **Download** datasets from remote or local sources.
- **Process** and reproject GeoTIFF files to EPSG:4326.
- **Store** the processed data in a PostgreSQL/PostGIS database.
- **Query** the database for specific geometries or Sentinel-2 tiles.


## Installation

**Step 1: Clone the repository**

```bash
git clone https://github.com/noah-kr/bt-biomass-datasets.git
```

```bash
cd bt-biomass-datasets
```

**Step 2: Set Up the Environment (only for Linux users)**

To create a conda environment with all the necessary dependencies, use the provided environment.yml file:
```bash
conda env create -f environment.yml
```
Activate the environment: 
```bash
conda activate bmproject
```

## Downloading Datasets
The repository supports multiple datasets. Follow the instructions below to download each dataset. Each script will ask you for the target directory to store the datasets.

Note: If the downloading process gets interrupted, you can just re-run the script and it will continue where it left off.

### 1. Open-Canopy Dataset (France)
To download the Open-Canopy Dataset France, use the provided script download_open_canopy.py within the conda environment.
(adapt script to not download spot data)
- Note: you need about 380GB available to download this dataset.

**Run the script:**
```markdown
python download_open_canopy.py
```


### 2. AGB Dataset (China)

To download the AGB Dataset China, use the provided script download_AGB_China.py. The script will only download data form 2015 onwards. Older data will be ignored.

- Note: You need about 108GB available to download this dataset

**Run the script:**
```markdown
python download_AGB_China.py
```

### 3. LiDAR AGB Dataset (South Asia and Central Africa)

Follow the steps below to manually download the dataset:

1. **Visit the Dataset Page**  
   Open the [Dataverse dataset page](https://dataverse.ird.fr/dataset.xhtml?persistentId=doi:10.23708/H2MHXF) in your browser.

2. **Locate the "Access Dataset" Button**  
   On the dataset page, look for the blue button labeled **"Access Dataset"** on the right-hand side.

3. **Select a Download Option**
   - Click on the **"Access Dataset"** button to open the dropdown menu.
   - Select **"Original Format ZIP (9.1 MB)"**

4. **Accept Dataset Terms**  
   After selecting a download option, a pop-up window with the dataset's terms of use will appear.
   - Read and review the terms.
   - Click the **"Accept"** button to confirm and start the download.


### 4. LANDFIRE 2022 Canopy Height Dataset (US)

Follow the steps below to manually download the dataset:

1. **Visit the Dataset Page**  
   The Landfire dataset consists of four different regions. You will have to download the data for each region manually. Here are the links for each dataset, please follow the instruction below to download the data.

   [LANDFIRE Canopy Height Conus](https://www.sciencebase.gov/catalog/item/64f2465fd34e095955171e11)
   [LANDFIRE Canopy Height Alaska](https://www.sciencebase.gov/catalog/item/64f24e34d34e095955171e94)
   [LANDFIRE Canopy Height Hawaii](https://www.sciencebase.gov/catalog/item/65665fead34e3aa43a43faae)
   [LANDFIRE Canopy Height Puerto Rico](https://www.sciencebase.gov/catalog/item/655542f8d34ee4b6e05c463b)

2. **Download the data**  
   After opening the link, scroll to the section "Attached Files" and click on the zip file (e.g. LF2022_CH_230_CONUS_20231026.zip). Then complete the captcha and click on "Download File". Repeat this for every link above.


## Reproject to EPSG:4326 and compress the data
In order to get the correct results when querying, we have to reproject the data to EPSG:4326. To save space we will also LWZ compress the files while reprojecting.

**Note:**
- The AGB China dataset is already in EPSG:4326 so it does not require reprojection or compression. The script will ask you for the input and output folder, please don't input the AGB China dataset here.
- In the Open-Canopy dataset the folder lidar_classification and spot will not be relevant to our database. To avoid unnecessary computations you should either delete these folders or move them to a different directory before using the script.
- This script will run for a while. If it gets interrupted you can just restart it and it will pick up where it left off. In case it gets interrupted while processing a file, the file might only partially be processed, so you should delete this file and then restart the script.

**Run the script:**
```bash
python reproject_data.py
```


## Database Setup

**1. Start the PostgreSQL server:**

Replace "/path/to/data/directory" with the directory where the pgsql_data folder is stored
```bash
pg_ctl -D /path/to/data/directory start
```
In my specific case:
```bash
 pg_ctl -D /scratch/nkreyenkamp/pgsql_data start
```


**2. Run the provided script setup_database.py to setup the database and schema:**
```bash
python setup_database.py
```

**You can stop the PostgreSQL server with this command:**
```bash
pg_ctl -D /path/to/data/directory stop
```



## Loading Data into the Database

### 1. General script to load data into database

If you have a folder of GeoTIFF files that you want to add to the database, you can execute the following script. The script will ask you for the necessary parameters like location of the data etc.

```bash
python load_data_general.py
```

### 2. Dataset-Specific Scripts

Note: Please make sure to give the location of the **reprojected** datasets when prompted

- **Open-Canopy Dataset France**
Note: Make sure to delete or move The folder lidar_classification and spot, since this data is not relevant for the database

```bash
python load_open_canopy.py
```

- **AGB Dataset (China)**
```bash
python load_AGB_china.py
```

- **LiDAR AGB Dataset (South Asia and Central Africa)**
Put both folders "LiDAR-based_biomass_maps_Central_Africa" and "LiDAR-based_biomass_maps_South_Asia" into the same folder and input this folder as the root directory when prompted
```bash
python load_AGB_south_asia_central_africa.py
```

- **LANDFIRE 2022 Canopy Height Dataset (US)**

```bash
python load_landfire.py
```


### Querying the Database:

#### 1. Query a Point
This query will check for TIFF files containing the specified point and returns their directory locations.

```bash
python query_point.py
```

#### 2. Query a Geometry
Find TIFF files intersecting a user-defined geometry in WKT format:
```bash
python query_geometry.py
```
- Note: The output TIFF file will always be in EPSG:4326, even if the input is in a different CRS format

#### 3. Sentinel-2 Tile Conversion
Convert Sentinel-2 tile names to WKT geometries:
```bash
python convert_sentinel_tile.py
```

## Usage on pf-pc18
- All relevant data is stored on pf-pc18 in the folder ```/scratch/nkreyenkamp```.
- Script and data can be found in ```/scratch/nkreyenkamp/biomass_project```.
- Name of the Anaconda environment is ```bmproject```
- Start the database server: ```pg_ctl -D /scratch/nkreyenkamp/pgsql_data start```
- Stop the database server: ```pg_ctl -D /scratch/nkreyenkamp/pgsql_data stop```
- Open database: ```psql -d bmdata```






