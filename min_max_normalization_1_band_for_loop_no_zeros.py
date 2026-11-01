import numpy as np
import rasterio
from rasterio.enums import Resampling

import os
import tifffile as tiff

folder_path = "/home/george/Desktop/test_code/Vegetation_Indices/BGR"
#folder_path = "/home/george/Desktop/test_code/Vegetation_Indices/GRRN"

images = []

for filename in os.listdir(folder_path):
    if filename.lower().endswith(".tif"):
        file_path = os.path.join(folder_path, filename)
        img = tiff.imread(file_path)
        images.append(img)
        print(file_path)

        input_path = file_path #"input.tif"
        output_path = f"{filename}_MIN_MAX.tif"

        with rasterio.open(input_path) as src:
            image = src.read(1).astype(np.float32)
            profile = src.profile

        min_val = image.min()
        max_val = image.max()

        #if max_val > min_val:
        normalized = (image - min_val) / (max_val - min_val)
        #else:
            #normalized = np.zeros_like(image)

        # Update profile for output
        profile.update(dtype=rasterio.float32, count=1)

        #normalized_uint8 = (normalized * 255).astype(np.uint8)

        with rasterio.open(output_path, "w", **profile) as dst:
            #dst.write(normalized_uint8, 1)
            dst.write(normalized, 1)

        print("Georeferenced normalization completed.")
