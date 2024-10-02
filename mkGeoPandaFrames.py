#
# Calculate a set of GeoPandaFrames from a QuadContourSet object
#
# Jan-2022, Pat Welch, pat@mousebrains

import geopandas as gpd
from shapely.geometry import LineString

def mkGeoPandaFrames(b) -> list:
    frames = []
    for index in range(b.levels.size):
        level = int(round(b.levels[index]))
        segs = b.allsegs[index]
        print("Level", level, len(segs))
        for seg in segs:
            if seg.shape[0] == 0: continue
            df = gpd.GeoDataFrame(
                    data={"Depth": [level], "geometry": LineString(seg)},
                    crs = "EPSG:4326",
                    )
            frames.append(df)
    return frames
