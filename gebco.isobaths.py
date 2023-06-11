#! /usr/bin/env python3
#
# Generate isobaths from GEBCO gridded bathymetry NetCDF file.
#
# Jan-2022, Pat Welch, pat@mousebrains

from argparse import ArgumentParser
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
from shapely.geometry import LineString
import matplotlib.pyplot as plt
import time
import sys

def mkLevels(contours:tuple[str]) -> np.array:
    levels = []
    for contour in contours:
        for level in contour.split(","):
            try:
                levels.append(int(level))
            except Exception as e:
                print("Unable to convert", level, "to a floating point number")
                print(str(e))
                sys.exit(1)
    return np.array(sorted(levels))

def pruneData(elevation:xr.DataArray, latkey,latmin,latmax, lonkey,lonmin,lonmax) -> xr.DataArray:
    if latmin is None and latmax is None:
        if lonmin is None and lonmax is None: return elevation
        return elevation.sel({lonkey: slice(lonmin, lonmax)})
    elif lonmin is None and lonmax is None:
        if latmin is None and latmax is None: return elevation
        return elevation.sel({latkey: slice(latmin, latmax)})
    return elevation.sel({latkey: slice(latmin, latmax), lonkey: slice(lonmin, lonmax)})

parser = ArgumentParser()
parser.add_argument("--nc", type=str, required=True, help="NetCDF data source from GEBCO")
parser.add_argument("--shp", type=str, required=True, help="Output shapefile name")
parser.add_argument("--latmin", type=float, help="Latitude minimum in decimal degrees")
parser.add_argument("--latmax", type=float, help="Latitude maximum in decimal degrees")
parser.add_argument("--lonmin", type=float, help="Longitude minimum in decimal degrees")
parser.add_argument("--lonmax", type=float, help="Longitude maximum in decimal degrees")
parser.add_argument("--contour", type=str, action="append",
        help="Isobath contour level(s), comma deliminated")
parser.add_argument("--plot", action="store_true", help="Generate plot")
args = parser.parse_args()

if args.contour is None:
    levels = np.array([10, 20, 50, 100, 200, 500, 1000, 2000])
else:
    levels = mkLevels(args.contour)

stime = time.time()
frames = []
with xr.open_dataset(args.nc) as ds: # Get the data
    depth = -pruneData(ds.elevation, 
            "lat", args.latmin, args.latmax, "lon", args.lonmin, args.lonmax)
    print("Took", time.time()-stime, "to select data")
    stime = time.time()
    b = xr.plot.contour(depth, levels=levels) # Make the contours
    print("Took", time.time()-stime, "to make contours")
    if args.plot:
        plt.grid(True)
        plt.xlabel("Longitude (deg)")
        plt.ylabel("Latitude (deg)")
        plt.show()

    stime = time.time()
    for i in range(levels.size):
        for path in b.collections[i].get_paths():
            if path.vertices.shape[0] < 2: continue # Skip contour segments which are too short
            df = gpd.GeoDataFrame(data={
                "Depth": [levels[i]],
                "geometry": LineString(path.vertices),
                },
                crs = "EPSG:4326",
                )
            frames.append(df)
    print("Took", time.time()-stime, "to make", len(frames), "GDF frames")

gdf = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True))
print(gdf)

stime = time.time()
gdf.to_file(args.shp)
print("Took", time.time()-stime, "to save", args.shp)
