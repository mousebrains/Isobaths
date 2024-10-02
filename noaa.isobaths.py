#! /usr/bin/env python3
#
# Generate isobaths from NOAA gridded bathymetry NetCDF file.
#
# Jan-2022, Pat Welch, pat@mousebrains

from argparse import ArgumentParser
import xarray as xr
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import time
from mkLevels import mkLevels
from pruneData import pruneData
from mkGeoPandaFrames import mkGeoPandaFrames

parser = ArgumentParser()
parser.add_argument("--nc", type=str, required=True, help="NetCDF data source from NOAA")
parser.add_argument("--shp", type=str, required=True, help="Output shapefile name")
parser.add_argument("--latmin", type=float, help="Latitude minimum in decimal degrees")
parser.add_argument("--latmax", type=float, help="Latitude maximum in decimal degrees")
parser.add_argument("--lonmin", type=float, help="Longitude minimum in decimal degrees")
parser.add_argument("--lonmax", type=float, help="Longitude maximum in decimal degrees")
parser.add_argument("--contour", type=str, action="append",
        help="Isobath contour level(s), comma deliminated")
parser.add_argument("--plot", action="store_true", help="Generate plot")
args = parser.parse_args()

levels = mkLevels(args.contour)

stime = time.time()
frames = []
with xr.open_dataset(args.nc) as ds: # Get the data
    depth = -pruneData(ds.Band1, 
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
    frames = mkGeoPandaFrames(b)
    print("Took", time.time()-stime, "to make", len(frames), "GDF frames")

gdf = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True))
print(gdf)

stime = time.time()
gdf.to_file(args.shp)
print("Took", time.time()-stime, "to save", args.shp)
