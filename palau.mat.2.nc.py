#! /usr/bin/env python3
#
# Read in Harper's bathymetry Matlab file and generate
# GEBCO style file for making contours
#
# March-2023, Pat Welch, pat@mousebrains.com

from argparse import ArgumentParser
import xarray as xr

parser = ArgumentParser()
parser.add_argument("input", type=str, help="Input .mat filename")
parser.add_argument("output", type=str, help="Output .nc filename")
args = parser.parse_args()

with xr.open_dataset(args.input, engine="netcdf4") as ds:
    ds = ds.drop(("res", "mb_mask", "pc_mask", "bb", "README"))
    ds = ds.squeeze()
    ds = ds.set_coords(("lat", "lon"))
    ds = ds.swap_dims(phony_dim_3 = "lon", phony_dim_4 = "lat")
    ds = ds.rename(D = "elevation")
    ds = ds.assign(elevation = -ds.elevation.transpose())
    print(ds)
    ds.to_netcdf(args.output)
