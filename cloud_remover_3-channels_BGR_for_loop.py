import numpy as np
import rasterio
from rasterio.enums import Resampling

import os
import tifffile as tiff

folder_path = "/home/george/Desktop/test_code/3-BANDS-BGR-TIFS"
images = []

for filename in os.listdir(folder_path):
    if filename.lower().endswith(".tif"):
        file_path = os.path.join(folder_path, filename)
        img = tiff.imread(file_path)
        images.append(img)
        print(file_path)
        
        bgr_path = file_path
        bgr_cloudfree_path = f"{filename}_cloud_free.tif" #"BGR_cloudfree.tif"

        # Function to create cloud mask
        def mask_clouds(data, thresholds):
            """
            data: numpy array (bands, height, width)
            thresholds: list of thresholds for each band
            returns: cloud mask
            """
            mask = np.zeros(data.shape[1:], dtype=bool)
            for i, thresh in enumerate(thresholds):
                mask |= data[i] > thresh
            return mask

        # 1️D Process BGR
        with rasterio.open(bgr_path) as src:
            bgr = src.read()
            profile = src.profile

        # Adjust thresholds based on your image (DN values)
        bgr_thresholds = [0.1, 0.1, 0.1]  # Blue, Green, Red
        cloud_mask_bgr = mask_clouds(bgr, bgr_thresholds)

        # Apply mask
        nodata = profile.get("nodata", 0)
        bgr[:, cloud_mask_bgr] = nodata

        with rasterio.open(bgr_cloudfree_path, "w", **profile) as dst:
            dst.write(bgr)
