# Isobaths

Generate isobath (constant-depth) contour lines from gridded bathymetry
NetCDF files and write them to GIS vector files (ESRI Shapefile, GeoPackage,
or GeoJSON).

## Installation

The tools need the scientific Python + geospatial stack. Create a virtual
environment and install the pinned dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

(or, with [`uv`](https://github.com/astral-sh/uv): `uv venv && uv pip install -r requirements.txt`.)

## Data sources

- **GEBCO** — download the *2D* NetCDF grid for your region from
  [GEBCO](https://download.gebco.net). Elevation variable: `elevation`.
- **NOAA** — download a DEM from
  [NOAA NCEI](https://www.ncei.noaa.gov/maps/bathymetry/). Elevation
  variable: `Band1`. NOAA grids are frequently stored north-to-south
  (descending latitude); this is handled automatically.

Both conventions store **elevation** (negative below sea level); the tools
negate it internally so that `--contour` levels are given as positive depths
in metres.

## Usage

```bash
# GEBCO
./gebco.isobaths.py --nc=GEBCO.nc --shp=out.shp \
    --latmin=0 --latmax=26 --lonmin=99 --lonmax=124 \
    --contour=50,100,200 --contour=500,1000

# NOAA
./noaa.isobaths.py --nc=noaa_dem.nc --shp=out.gpkg --contour=10,20,50,100
```

Key options (see `--help` for the full list):

| Option | Meaning |
| --- | --- |
| `--nc` | Input NetCDF grid (required) |
| `--shp` | Output vector file; format inferred from extension `.shp`/`.gpkg`/`.geojson` (required) |
| `--contour` | Comma-delimited **integer** depth levels in metres; repeatable. Duplicates are de-duplicated. Defaults to `10,20,50,100,200,500,1000,2000` |
| `--latmin/--latmax/--lonmin/--lonmax` | Optional bounding box in decimal degrees |
| `--variable` | Elevation variable name (default `elevation` for GEBCO, `Band1` for NOAA) |
| `--latname/--lonname` | Coordinate names (default `lat`/`lon`) |
| `--plot` | Display a plot of the contours |

Output is written in EPSG:4326 (WGS84 lon/lat) with a single integer `Depth`
attribute per line.

Both `gebco.isobaths.py` and `noaa.isobaths.py` are thin wrappers around the
shared driver in `isobaths.py`; they differ only in the default variable name.

## Helper scripts

- `vietnam` — example driver producing shallow and deep isobath sets for the
  Vietnam region from a global GEBCO grid.
- `palau.mat.2.nc.py` — convert a Matlab `.mat` bathymetry file into a
  GEBCO-style NetCDF that `gebco.isobaths.py` can consume.

## Development

```bash
pip install -r requirements.txt   # includes pytest
pytest                            # runs the suite on small synthetic grids
```

The tests build synthetic GEBCO-style (ascending latitude) and NOAA-style
(descending latitude) grids, so no real DEM download is needed to run them.
