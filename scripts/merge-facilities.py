import os
import geopandas as gpd
import pandas as pd

def merge_geojson_files(search_term, input_dir="GeoJSONs"):
    def list_all_files(directory):
        file_list = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_list.append(os.path.join(root, file))
        return file_list

    # Get the list of all files in the subfolders
    all_files = list_all_files(input_dir)

    # List to store GeoDataFrames from all matching files
    gdfs = []

    # Iterate through all files and process those containing the search term
    for file_path in all_files:
        if search_term in os.path.basename(file_path):
            print(f"Matching file: {file_path}")
            gdf = gpd.read_file(f"GeoJSON:{file_path}")
            gdf = gdf.to_crs(epsg=4326)  # Transform to common CRS (WGS 84)
            gdfs.append(gdf)

    # Check if there are any GeoDataFrames to concatenate
    if gdfs:
        # Concatenate all GeoDataFrames into a single GeoDataFrame
        combined_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))

        # Save the combined GeoDataFrame to the working directory as a GeoJSON file
        output_file = f"data/Vermont{search_term}.geojson"
        combined_gdf.to_file(output_file, driver="GeoJSON")

        print(f"Combined GeoJSON saved to {output_file}")
    else:
        print("No matching files found.")


# Example usage
# merge_geojson_files("Border")
# merge_geojson_files("LinearFeatures")
# merge_geojson_files("PointFeatures")
# merge_geojson_files("ServiceArea")
merge_geojson_files("WWTF")