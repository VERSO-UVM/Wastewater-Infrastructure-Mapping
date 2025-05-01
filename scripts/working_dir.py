import os

# Get the current working directory
current_directory = os.getcwd()

# Print the current working directory
print(f"The current working directory is: {current_directory}")

import os

def list_all_files(directory):
    file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_list.append(os.path.join(root, file))
    return file_list

# Directory containing the GeoJSON files
geojson_dir = "GeoJSONs"

# Get the list of all files in the subfolders
all_files = list_all_files(geojson_dir)

# Print the list of all files
for file in all_files:
    print(file)
