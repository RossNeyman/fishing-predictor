# Fishing Predictor

A data-driven project that predicts saltwater fishing outcomes by combining recreational survey data with NOAA/NDBC weather and tide measurements. The pipeline cleans raw survey files, merges hourly buoy and tide data, engineers trip-window features (wind, pressure, temperature, water level, sun/moon events), and produces model-ready datasets for training and evaluation.

## Project Context
This work was completed for CSC 594, guided by Dr. Sarah Zelikovitz at the College of Staten Island.

## Contents
- `data/`: raw and processed datasets
- `notebooks/`: EDA and feature-engineering workflows
- `pipelines/noaa_data_pipeline/`: NOAA data ingestion utilities
- `Frontend/`: lightweight app for running the model
- `model/`: trained model artifacts

## Quick Start
1. Install dependencies:  
   `pip install -r Frontend/requirements.txt`
2. Run the app:  
   `python Frontend/app.py`
3. Or visit the hosted demo:  
   https://rossneyman-fishing-predict-catch.hf.space/

## Notes
Processed datasets are in `data/processed/`, including joined weather/tide tables and the final engineered trip dataset used for training.