import numpy as np
import rasterio
from rasterio.enums import Resampling

import os
import tifffile as tiff

folder_path = "/home/george/Desktop/test_code/4-BANDS-GRRN-TIFS"
images = []

for filename in os.listdir(folder_path):
    if filename.lower().endswith(".tif"):
        file_path = os.path.join(folder_path, filename)
        img = tiff.imread(file_path)
        images.append(img)
        print(file_path)

        grrn_path = file_path
        grrn_cloudfree_path = f"{filename}_cloud_free.tif" 

        # Function to create cloud mask
        def mask_clouds(data, thresholds):
            mask = np.ones(data.shape[1:], dtype=bool)

            for i, (op, val) in enumerate(thresholds):
                if op == ">":
                    mask &= data[i] > val
                elif op == "<":
                    mask &= data[i] < val
                else:
                    raise ValueError(f"Unknown operator: {op}")
            return mask

        # 2️D Process GRRN
        with rasterio.open(grrn_path) as src:
            grrn = src.read()
            profile = src.profile

        # Thresholds for GRRN (Green, Red, RedEdge, NIR)
        grrn_thresholds = grrn_thresholds = [
            (">", 0.1),
            (">", 0.1),
            ("<", 0.24),
            ("<", 0.26),
        ]
        cloud_mask_grrn = mask_clouds(grrn, grrn_thresholds)

        # Apply mask
        nodata = profile.get("nodata", 0)
        grrn[:, cloud_mask_grrn] = nodata

        with rasterio.open(grrn_cloudfree_path, "w", **profile) as dst:
            dst.write(grrn)

        print("Cloud masking completed for BGR and GRRN")
