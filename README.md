# DWD Climate Data Pipeline

A reproducible geospatial data pipeline for transforming gridded climate raster data from the German Weather Service (DWD) into regional time series and analysis-ready datasets.

The pipeline downloads DWD Climate Data Center (CDC) raster data, converts and validates the source files, reprojects and clips them to a study area, calculates regional statistics, and exports the results as CSV and NetCDF.

The aggregation method depends on the variable and dimension being aggregated. Regional raster values are typically calculated using a spatial mean, while precipitation may be summed when aggregating across time.

The current calculate_regional_mean() function uses data.mean() to calculate the spatial mean across the study area. Temporal aggregation, such as summing precipitation across days or months, should be applied separately to the resulting time series.

The municipality of Kerpen, Germany, is used as a case study, based on climate adaptation work carried out within the ARKE research project.

## Workflow

The pipeline performs the following steps:

1. Download monthly gridded climate data from the DWD Climate Data Center
2. Decompress downloaded ASCII raster files
3. Convert ASCII grids to GeoTIFF using GDAL
4. Validate raster CRS, resolution, temporal coverage, and file completeness
5. Reproject the study-area boundary to the raster CRS
6. Clip rasters to the study area
7. Calculate monthly regional mean values
8. Validate the resulting time series
9. Export results to CSV and NetCDF

## Outputs

The pipeline produces:

- monthly GeoTIFF rasters clipped to the study area
- a regional monthly time series as CSV
- a NetCDF dataset
- validated intermediate datasets for further spatial or temporal analysis

The default configuration uses monthly DWD soil-moisture data, but the workflow can be adapted to other gridded DWD datasets such as precipitation or temperature by changing the dataset configuration.

## Case Study: Kerpen

Kerpen is used as the study area for this repository.

The example builds on work from the ARKE research project (*Adapting to the consequences of climate change for the Kolpingstadt Kerpen*), which focused on municipal climate impacts, climate-risk assessment, and adaptation planning.

The pipeline demonstrates how national gridded climate datasets can be transformed into municipality-level indicators that can be used for climate analysis, visualization, and decision support.

More information about the ARKE project:

https://www.th-koeln.de/en/spatial-development-and-infrastructure-systems/arke---adapting-to-the-consequences-of-climate-change-for-the-kolpingstadt-kerpen_113290.php

The study area can be replaced with another municipality or regional boundary, allowing the same processing workflow to be reused elsewhere in Germany.

## Tech Stack

- Python
- Rasterio
- GeoPandas
- GDAL
- pandas
- NumPy
- xarray
- rioxarray

## Visualizations

The generated CSV and NetCDF outputs can be used for follow-up climate analysis and visualization.

Example outputs include:

- monthly soil-moisture time series
- long-term climate trends
- seasonal variability
- anomaly analysis
- maps of clipped climate rasters


## Installation

### Windows (Anaconda / Conda)

On Windows, Conda is recommended because the pipeline depends on GDAL and other geospatial libraries.

Create the environment from `environment.yml`:

```bat
conda env create -f environment.yml

conda activate dwd_pipeline

python -m src.pipeline