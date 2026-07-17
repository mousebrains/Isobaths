#
# Shared driver for generating isobath contours from a gridded bathymetry
# NetCDF file and writing them to a vector file (shapefile, GeoPackage, ...).
#
# gebco.isobaths.py and noaa.isobaths.py are thin wrappers around main(),
# differing only in the default elevation variable name.
#
# Jan-2022, Pat Welch, pat@mousebrains.com

import sys
import time
from argparse import ArgumentParser


def build_parser(default_variable: str, source: str) -> ArgumentParser:
    parser = ArgumentParser(
        description=f"Generate isobaths from a {source} gridded bathymetry NetCDF file"
    )
    parser.add_argument("--nc", type=str, required=True, help=f"NetCDF data source from {source}")
    parser.add_argument(
        "--shp", type=str, required=True, help="Output vector file (.shp, .gpkg, or .geojson)"
    )
    parser.add_argument(
        "--variable",
        type=str,
        default=default_variable,
        help=f"Elevation variable name (default: {default_variable})",
    )
    parser.add_argument(
        "--latname", type=str, default="lat", help="Latitude coordinate name (default: lat)"
    )
    parser.add_argument(
        "--lonname", type=str, default="lon", help="Longitude coordinate name (default: lon)"
    )
    parser.add_argument("--latmin", type=float, help="Latitude minimum in decimal degrees")
    parser.add_argument("--latmax", type=float, help="Latitude maximum in decimal degrees")
    parser.add_argument("--lonmin", type=float, help="Longitude minimum in decimal degrees")
    parser.add_argument("--lonmax", type=float, help="Longitude maximum in decimal degrees")
    parser.add_argument(
        "--contour",
        type=str,
        action="append",
        help="Isobath level(s) in metres, comma delimited; repeatable",
    )
    parser.add_argument("--plot", action="store_true", help="Display a plot of the contours")
    return parser


def run(args) -> int:
    # Imports are deferred so that --help stays instant and the heavy geo stack
    # is only loaded once arguments have been validated.
    import matplotlib
    import xarray as xr

    if not args.plot:
        matplotlib.use("Agg")  # no display needed when we only extract segments
    import matplotlib.pyplot as plt

    from mkGeoPandaFrames import mkGeoPandaFrames
    from mkLevels import mkLevels
    from pruneData import pruneData

    levels = mkLevels(args.contour)

    stime = time.perf_counter()
    with xr.open_dataset(args.nc) as ds:
        if args.variable not in ds:
            raise ValueError(
                f"Variable {args.variable!r} not found in {args.nc}; "
                f"available data variables: {list(ds.data_vars)}"
            )

        # GEBCO/NOAA store elevation (negative below sea level); negate to depth.
        depth = -pruneData(
            ds[args.variable],
            args.latname,
            args.latmin,
            args.latmax,
            args.lonname,
            args.lonmin,
            args.lonmax,
        )

        # Force canonical (lat, lon) order so extracted segments are always
        # (x=lon, y=lat), matching EPSG:4326 axis order, whatever the file's order.
        depth = depth.transpose(args.latname, args.lonname)

        if depth.size == 0:
            raise ValueError(
                "Selected region is empty -- check --lat*/--lon* bounds against "
                "the file's coverage."
            )
        print(f"Took {time.perf_counter() - stime:.2f}s to select a {depth.shape} grid")

        lon = depth[args.lonname].values
        lat = depth[args.latname].values

        stime = time.perf_counter()
        fig, ax = plt.subplots()
        cs = ax.contour(lon, lat, depth.values, levels=levels)
        print(f"Took {time.perf_counter() - stime:.2f}s to make contours")

        if args.plot:
            ax.grid(True)
            ax.set_xlabel("Longitude (deg)")
            ax.set_ylabel("Latitude (deg)")
            plt.show()

        stime = time.perf_counter()
        gdf = mkGeoPandaFrames(cs)
        plt.close(fig)  # release the figure; nothing leaks
        print(f"Took {time.perf_counter() - stime:.2f}s to build {len(gdf)} contour lines")

    if gdf.empty:
        raise ValueError(
            "No contours found for the requested levels within the region -- nothing written."
        )

    print(gdf)
    stime = time.perf_counter()
    gdf.to_file(args.shp)
    print(f"Took {time.perf_counter() - stime:.2f}s to save {args.shp}")
    return 0


def main(default_variable: str, source: str, argv=None) -> int:
    parser = build_parser(default_variable, source)
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
