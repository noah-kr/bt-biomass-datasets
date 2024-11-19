# Biomass and Canopy Height Database
This repository provides the scripts and instructions to set up, download, process, and query a database for above-ground biomass (AGB) and canopy height data, combining various datasets.

Authors: Noah Kreyenkamp


## Installation

**Step 1: Set Up the Environment**

To create a conda environment with all necessary dependencies, use the following commands:
```markdown
conda env create -f environment.yml
```
Activate the environment: 
```markdown
conda activate bmdata
```

**Step 2: Clone the repository**

```markdown
git clone https://github.com/noah-kr/bt-biomass-datasets.git
cd bt-biomass-datasets
```

## Downloading Datasets


### Download Open-Canopy Dataset France
To download the Open-Canopy Dataset France, use the provided script download_open_canopy.py within the bmdata Conda environment.

**1. Run the script:**
```markdown
python download_open_canopy.py
```

**2. Enter the target directory when prompted:**
```markdown
Enter the target directory for downloading the dataset: /path/to/your/directory
```


### Download AGB Dataset China

To download the AGB Dataset China, use the provided script download_AGB_China.py within the bmdata Conda environment.

**1. Run the script:**
```markdown
python download_AGB_China.py
```

**2. Enter the target directory when prompted:**
```markdown
Enter the target directory for downloading the dataset: /path/to/your/directory
```

### Download LiDAR AGB Dataset South Asia and Central Africa

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

5. **Save the Dataset**  
   The file will begin downloading. Save it to a location of your choice on your computer.


### Download LANDFIRE 2022 Canopy Height Dataset US

## Database Setup

## Using Database: Example Queries
