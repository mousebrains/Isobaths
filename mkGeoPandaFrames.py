#
# Build a GeoDataFrame of isobath contour lines from a matplotlib ContourSet.
#
# Segments are accumulated into plain lists and turned into a single
# GeoDataFrame at the end.  Building one frame per segment and concatenating
# thousands of them (the old approach) is dramatically slower for large grids.
#
# Jan-2022, Pat Welch, pat@mousebrains.com

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString


def mkGeoPandaFrames(cs, crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    depths = []
    geoms = []
    for index in range(cs.levels.size):
        level = int(round(cs.levels[index]))
        for seg in cs.allsegs[index]:
            # Need at least two points, and they must not all collapse to a
            # single location.  matplotlib occasionally emits a tiny closed
            # contour whose vertices are numerically identical, which yields a
            # zero-length (invalid) LineString.
            if seg.shape[0] < 2 or not np.ptp(seg, axis=0).any():
                continue
            depths.append(level)
            geoms.append(LineString(seg))
    return gpd.GeoDataFrame({"Depth": depths, "geometry": geoms}, crs=crs)
