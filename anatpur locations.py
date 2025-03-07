import pandas as pd
import plotly.express as px
import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
import requests

# Function to read the CSV file and return a DataFrame
def read_csv(url):
    response = requests.get(url)
    response.raise_for_status()  # Ensure we notice bad responses
    df = pd.read_csv(url, parse_dates=['time'])
    return df

# Function to filter the DataFrame based on year and tmax threshold
def filter_data(df, year, tmax_threshold):
    filtered_df = df[(df['time'].dt.year == year) & (df['tmax'] >= tmax_threshold)]
    return filtered_df

# Function to count the number of days meeting the tmax threshold for each lat/lon
def count_days_per_location(df, tmax_threshold):
    count_df = df[df['tmax'] >= tmax_threshold].groupby(['lat', 'lon']).size().reset_index(name='days_count')
    return count_df

# Function to create a map with points for latitude and longitude using Folium
def create_map(df, shapefile, tmax_threshold):
    gdf = gpd.read_file(shapefile)
    
    # Set CRS for the shapefile if not already set
    if gdf.crs is None:
        gdf.set_crs('EPSG:4326', inplace=True)
    
    # Filter shapefile for Anantapur and Sri Satya Sai districts
    filtered_gdf = gdf[gdf['DISTRICT'].isin(['Anantapur', 'Sri Satya Sai'])]
    
    # Create a Folium map centered around the mean latitude and longitude
    m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=8)
    
    # Add district boundaries to the map
    folium.GeoJson(filtered_gdf).add_to(m)
    
    # Add points from the CSV file to the map
    for _, row in df.iterrows():
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=f"Lat: {row['lat']}, Lon: {row['lon']}, Tmax: {row['tmax']}",
            tooltip=f"Lat: {row['lat']:.2f}<br>Lon: {row['lon']:.2f}<br>Days: {row['days_count']}",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
    
    return m

# Read the CSV file
file_path = "https://github.com/reinsuranceanalytics/Anantapur_tmax/blob/main/Anantapur_test.csv"      # Replace with your CSV file path
df = read_csv(file_path)

# File uploader for shapefile
shapefile = "https://github.com/reinsuranceanalytics/Anantapur_tmax/blob/main/Anantapur.json"

# Get unique years from the DataFrame
years = df['time'].dt.year.unique()

if shapefile is not None:
    # Dropdown for years
    year = st.slider('Years:',1979, 2024, 2024,1)

    # Slider for tmax threshold
    tmax_threshold = st.slider('Tmax Threshold:', min_value=float(df['tmax'].min()), max_value=float(df['tmax'].max()), step=1.0)

    # Filter data based on selected year and tmax threshold
    filtered_df = filter_data(df, year, tmax_threshold)

    # Count the number of days meeting the tmax threshold for each lat/lon
    days_count_df = count_days_per_location(filtered_df, tmax_threshold)

    # Merge the count data with the filtered data
    filtered_df = filtered_df.merge(days_count_df, on=['lat', 'lon'], how='left')

     # Create map with filtered data and shapefile
    m = create_map(filtered_df, shapefile, tmax_threshold)

    # Display map
    folium_static(m)

