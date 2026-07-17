#
# Subset an xarray DataArray to a lat/lon box.
#
# Handles coordinate axes stored in either ascending or descending order.
# xarray's label-based .sel(slice(a, b)) follows the coordinate's *storage*
# order, so for a descending axis (e.g. a NOAA DEM stored north-to-south) the
# slice bounds have to be reversed or the selection comes back empty.
#
# Jan-2022, Pat Welch, pat@mousebrains.com

import xarray as xr


def _axisSlice(coord: xr.DataArray, lo, hi):
    """Return a slice selecting [lo, hi] regardless of axis direction, or None."""
    if lo is None and hi is None:
        return None
    ascending = coord.size < 2 or bool(coord.values[0] <= coord.values[-1])
    return slice(lo, hi) if ascending else slice(hi, lo)


def pruneData(
    elevation: xr.DataArray, latkey: str, latmin, latmax, lonkey: str, lonmin, lonmax
) -> xr.DataArray:
    selection = {}

    latSlice = _axisSlice(elevation[latkey], latmin, latmax)
    if latSlice is not None:
        selection[latkey] = latSlice

    lonSlice = _axisSlice(elevation[lonkey], lonmin, lonmax)
    if lonSlice is not None:
        selection[lonkey] = lonSlice

    return elevation.sel(selection) if selection else elevation
