import pandas as pd

df=pd.read_parquet("../noaa_data_pipeline/data/coops/station=8518750/product=water_level/**/*.parquet")
df.head(30)