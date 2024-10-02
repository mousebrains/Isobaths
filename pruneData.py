#
# Prune an Xarray Dataset to a given lat/lon box
#
# Jan-2022, Pat Welch, pat@mousebrains

import xarray as xr

def pruneData(elevation:xr.DataArray, 
              latkey:str, latmin:float, latmax:float,
              lonkey:str, lonmin:float, lonmax:float,
              ) -> xr.DataArray:
    if latmin is None and latmax is None:
        if lonmin is None and lonmax is None:
            return elevation
        return elevation.sel({lonkey: slice(lonmin, lonmax)})

    if lonmin is None and lonmax is None:
        return elevation.sel({latkey: slice(latmin, latmax)})

    return elevation.sel({latkey: slice(latmin, latmax), lonkey: slice(lonmin, lonmax)})
