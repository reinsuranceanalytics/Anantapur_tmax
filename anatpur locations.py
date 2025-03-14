import pandas as pd
import plotly.express as px
import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
import requests

# Inject custom CSS to hide the profile icon
hide_profile_icon = """
    <style>
    /* Target the profile icon using its class */
    ._profileImage_gzau3_78 {
        display: none !important;
    }
    /* Alternatively, target using data-testid */
    [data-testid="appCreatorAvatar"] {
        display: none !important;
    }
    </style>
"""
st.markdown(hide_profile_icon, unsafe_allow_html=True)

# Function to read the CSV file and return a DataFrame
# Function to read the CSV file and return a DataFrame
def read_csv(url):
    response = requests.get(url)
    response.raise_for_status()  # Ensure we notice bad responses
    try:
        df = pd.read_csv(url)
    except pd.errors.ParserError as e:
        st.error(f"ParserError: {e}")
        # Attempt to read the file by skipping bad lines
        df = pd.read_csv(url, on_bad_lines='skip')

    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])
    else:
        st.error("Column 'time' not found in the CSV file.")
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
    m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=7, width='100%', height='400px')
    
    # Add custom CSS to the map
    m.get_root().html.add_child(folium.Element('''
        <style>
            #map { height: 400px !important; margin: 0 !important; padding: 0 !important; }
            .folium-map { height: 400px !important; margin: 0 !important; padding: 0 !important; }
        </style>
    '''))
    
    # Add district boundaries to the map
    folium.GeoJson(filtered_gdf).add_to(m)
    
    # Add points from the CSV file to the map
    for _, row in df.iterrows():
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=f"Lat: {row['lat']}, Lon: {row['lon']}, Tmax: {row['tmax']}",
            tooltip=f"Lat: {row['lat']:.2f}<br>Lon: {row['lon']:.2f}<br>Days: {row['days_count']}",
            icon=folium.Icon(color='red', icon='thermometer-full', prefix='fa')
        ).add_to(m)
    
    return m

# Read the CSV file
file_path = "https://raw.githubusercontent.com/reinsuranceanalytics/Anantapur_tmax/refs/heads/main/Anantapur_test.csv"      # Replace with your CSV file path
df = read_csv(file_path)

# File uploader for shapefile
shapefile = "https://raw.githubusercontent.com/reinsuranceanalytics/Anantapur_tmax/refs/heads/main/Anantapur.json"

# Get unique years from the DataFrame
if 'time' in df.columns:
    years = sorted(df['time'].dt.year.unique(), reverse=True)

    if shapefile is not None:
        st.markdown("#### Events from 15-Mar to 15-May for Selected Year & Threshold tmax")
        col1,col2 = st.columns([2,1])
        # Dropdown for years
        year = col1.selectbox('Select Year:',years)
    
       # Filter DataFrame based on selected year to calculate max tmax for that year
        df_filtered_by_year = df[df['time'].dt.year == year]
        max_tmax_for_year = float(df_filtered_by_year['tmax'].max()) if not df_filtered_by_year.empty else float(df['tmax'].max())

        # Slider for tmax threshold, with max_value set to the max tmax for the selected year
        tmax_threshold = col2.number_input(
            'Threshold tmax:', 
            min_value=38.0, 
            max_value=max_tmax_for_year,
            value = float(df['tmax'].min()),
            step=0.5
        )
    
        # Filter data based on selected year and tmax threshold
        filtered_df = filter_data(df, year, tmax_threshold)
    
        # Count the number of days meeting the tmax threshold for each lat/lon
        days_count_df = count_days_per_location(filtered_df, tmax_threshold)
    
        # Merge the count data with the filtered data
        filtered_df = filtered_df.merge(days_count_df, on=['lat', 'lon'], how='left')
    
         # Create map with filtered data and shapefile
        m = create_map(filtered_df, shapefile, tmax_threshold)
        
        # Display map
        with st.container():
            folium_static(m, height=400)  # Explicitly set width and height

# Convert date column to datetime if needed
df['time'] = pd.to_datetime(df['time'])

# Manually add village names
village_names = {
    (14.0, 78.0): 'Obuladevara Cheruvu',
    (14.7, 77.4): 'Simgampalli',
    (14.8, 77.4): 'Muddalapuram'
}
df['village'] = df.apply(lambda row: village_names.get((row['lat'], row['lon']), 'Unknown'), axis=1)

# Add a year column to the DataFrame
df['year'] = df['time'].dt.year

# Add a period column to differentiate between the two periods
df['period'] = df['time'].apply(lambda x: '15 Mar-15 Apr' if (x.month == 3 and x.day >= 15) or (x.month == 4 and x.day <= 15) else
                                ('16 Apr-15 May' if (x.month == 4 and x.day > 15) or (x.month == 5 and x.day <= 15) else None))

# Filter out rows where period is None
df = df[df['period'].notna()]

# Filter data where temperature exceeds the threshold
filtered_data = df[df['tmax'] >= tmax_threshold]

# Group by latitude, longitude, village, year, and period, then count the number of days
grouped_data = filtered_data.groupby(['lat', 'lon', 'village', 'year', 'period']).size().reset_index(name='count_of_days')

# Pivot the table to have lat, lon, village as rows and count_of_days for each year and period as columns
pivot_table = grouped_data.pivot_table(index=['lat', 'lon', 'village'], columns=['year', 'period'], values='count_of_days', fill_value=0)

pivot_table = pivot_table.sort_index(axis=1, ascending=False)

# Create MultiIndex for columns to show year and period in separate rows
pivot_table = pivot_table.reindex(columns=pd.MultiIndex.from_product([sorted(pivot_table.columns.levels[0]), ['15 Mar-15 Apr', '16 Apr-15 May']], names=['Year', 'Period']))

# Ensure the columns are sorted in the desired order: years in decreasing order, ranges in the specified order
pivot_table = pivot_table.reindex(columns=pd.MultiIndex.from_product([sorted(pivot_table.columns.levels[0], reverse=True), ['15 Mar-15 Apr', '16 Apr-15 May']], names=['Year', 'Period']))

# Reset index to get a clean table format
pivot_table.reset_index(inplace=True)

# Add back the headers for lat, lon, and village
pivot_table.columns = pd.MultiIndex.from_tuples([('','Lat'), ('','Lon'), ('','Village')] + [(str(year), period) for year, period in pivot_table.columns[3:]], names=['Year', 'Period'])

# Display dataframe with MultiIndex columns
with st.container():
    st.markdown('<style>.stDataFrame {margin-top: 0 !important; padding-top: 0 !important;}</style>', unsafe_allow_html=True)
    st.dataframe(pivot_table, use_container_width=True)
