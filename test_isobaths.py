#
# Test suite for the Isobaths toolkit.
#
# Uses small synthetic GEBCO-style (ascending latitude) and NOAA-style
# (descending latitude) grids so the whole pipeline can be exercised without
# downloading real DEM files.  Run with:  pytest
#

from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from mkGeoPandaFrames import mkGeoPandaFrames
from mkLevels import mkLevels
from pruneData import pruneData

DATA = Path(__file__).parent / "tests" / "data"
GEBCO_SUBSET = DATA / "gebco_vietnam_subset.nc"  # real GEBCO, ascending lat
ETOPO_SUBSET = DATA / "etopo_monterey_subset.nc"  # real ETOPO, altitude/latitude/longitude


# --------------------------------------------------------------------------- #
# mkLevels
# --------------------------------------------------------------------------- #


def test_mklevels_default_when_none_or_empty():
    assert list(mkLevels(None)) == [10, 20, 50, 100, 200, 500, 1000, 2000]
    assert list(mkLevels([])) == [10, 20, 50, 100, 200, 500, 1000, 2000]


def test_mklevels_sorted_and_deduped():
    # 100 appears in both lists; the old code produced [0,50,100,100,200]
    # which crashes matplotlib ("Contour levels must be increasing").
    assert list(mkLevels(["0,50,100", "100,200"])) == [0, 50, 100, 200]


def test_mklevels_tolerates_whitespace_and_trailing_commas():
    assert list(mkLevels([" 10 , 20 ,"])) == [10, 20]


def test_mklevels_raises_on_non_integer():
    with pytest.raises(ValueError):
        mkLevels(["abc"])


def test_mklevels_raises_on_float_string():
    # Integer levels are an intentional design choice (Depth is an int field).
    with pytest.raises(ValueError):
        mkLevels(["1.5"])


# --------------------------------------------------------------------------- #
# Fixtures: a sloping "bowl" of bathymetry
# --------------------------------------------------------------------------- #


@pytest.fixture
def bowl():
    """lon, lat (ascending), elevation (negative below sea level)."""
    lon = np.linspace(99, 124, 120)
    lat = np.linspace(0, 26, 130)
    LON, LAT = np.meshgrid(lon, lat)
    depth = 50 + 100 * np.hypot(LON - 111, LAT - 13)  # metres, positive
    return lon, lat, -depth  # elevation


def _da(lon, lat, elev, descending=False):
    if descending:
        lat = lat[::-1]
        elev = elev[::-1, :]
    return xr.DataArray(elev, coords={"lat": lat, "lon": lon}, dims=("lat", "lon"))


# --------------------------------------------------------------------------- #
# pruneData
# --------------------------------------------------------------------------- #


def test_prune_ascending_selects_box(bowl):
    lon, lat, elev = bowl
    sub = pruneData(_da(lon, lat, elev), "lat", 5, 20, "lon", 105, 118)
    assert sub.size > 0
    assert float(sub.lat.min()) >= 5 and float(sub.lat.max()) <= 20
    assert float(sub.lon.min()) >= 105 and float(sub.lon.max()) <= 118


def test_prune_descending_latitude_matches_ascending(bowl):
    # The headline bug: a descending latitude axis used to return an empty box.
    lon, lat, elev = bowl
    asc = pruneData(_da(lon, lat, elev), "lat", 5, 20, "lon", 105, 118)
    desc = pruneData(_da(lon, lat, elev, descending=True), "lat", 5, 20, "lon", 105, 118)
    assert desc.size == asc.size > 0
    assert set(np.round(desc.lat.values, 6)) == set(np.round(asc.lat.values, 6))


def test_prune_no_bounds_is_identity(bowl):
    lon, lat, elev = bowl
    da = _da(lon, lat, elev)
    assert pruneData(da, "lat", None, None, "lon", None, None).size == da.size


def test_prune_partial_bounds(bowl):
    lon, lat, elev = bowl
    sub = pruneData(_da(lon, lat, elev), "lat", 10, None, "lon", None, None)
    assert float(sub.lat.min()) >= 10
    assert float(sub.lon.min()) == pytest.approx(99)  # lon untouched


# --------------------------------------------------------------------------- #
# mkGeoPandaFrames
# --------------------------------------------------------------------------- #


def _contourset(lon, lat, depth, levels):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    cs = ax.contour(lon, lat, depth, levels=levels)
    plt.close(fig)
    return cs


def test_mkgeopandaframes_builds_valid_lines(bowl):
    lon, lat, elev = bowl
    cs = _contourset(lon, lat, -elev, [200, 500, 1000])
    gdf = mkGeoPandaFrames(cs)
    assert not gdf.empty
    assert set(gdf.Depth.unique()).issubset({200, 500, 1000})
    assert gdf.crs.to_epsg() == 4326
    assert (gdf.geometry.type == "LineString").all()
    assert gdf.geometry.is_valid.all()


def test_mkgeopandaframes_empty_when_levels_out_of_range(bowl):
    lon, lat, elev = bowl
    cs = _contourset(lon, lat, -elev, [999999])
    assert mkGeoPandaFrames(cs).empty


class _FakeContourSet:
    """Minimal stand-in for a matplotlib ContourSet (levels + allsegs)."""

    def __init__(self, levels, allsegs):
        self.levels = np.array(levels)
        self.allsegs = allsegs


def test_mkgeopandaframes_skips_degenerate_segments():
    # Real GEBCO data produces a tiny closed contour whose vertices are all
    # identical -> a zero-length, invalid LineString.  It must be dropped.
    good = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 0.0]])
    all_identical = np.array([[5.0, 5.0]] * 4)  # >= 2 rows, zero extent
    single_point = np.array([[9.0, 9.0]])  # < 2 rows
    cs = _FakeContourSet([100], [[good, all_identical, single_point]])
    gdf = mkGeoPandaFrames(cs)
    assert len(gdf) == 1  # only the good segment survives
    assert gdf.geometry.is_valid.all()


# --------------------------------------------------------------------------- #
# Real-data regression fixtures (small subsets committed under tests/data)
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not GEBCO_SUBSET.exists(), reason="GEBCO fixture missing")
def test_real_gebco_subset_produces_valid_isobaths(tmp_path):
    import geopandas as gpd

    from isobaths import main

    out = tmp_path / "g.gpkg"
    rc = main(
        "elevation",
        "GEBCO",
        argv=["--nc", str(GEBCO_SUBSET), "--shp", str(out), "--contour", "500,1000,2000"],
    )
    assert rc == 0
    g = gpd.read_file(out)
    assert not g.empty
    # This subset contains a degenerate contour segment; every output line
    # must nonetheless be a valid geometry (guards mkGeoPandaFrames' skip).
    assert g.geometry.is_valid.all()
    assert (g.geometry.type == "LineString").all()
    assert set(g.Depth.unique()).issubset({500, 1000, 2000})
    assert g.crs.to_epsg() == 4326


@pytest.mark.skipif(not GEBCO_SUBSET.exists(), reason="GEBCO fixture missing")
def test_real_gebco_descending_matches_ascending(tmp_path):
    import geopandas as gpd

    from isobaths import main

    box = ["--contour", "500,1000,2000"]

    asc = tmp_path / "asc.gpkg"
    assert (
        main("elevation", "GEBCO", argv=["--nc", str(GEBCO_SUBSET), "--shp", str(asc), *box]) == 0
    )

    # Flip the real grid north-to-south and confirm identical isobaths.
    ds = xr.open_dataset(GEBCO_SUBSET)
    flipped = ds.isel(lat=slice(None, None, -1))
    desc_nc = tmp_path / "desc.nc"
    flipped.to_netcdf(desc_nc)
    ds.close()

    desc = tmp_path / "desc.gpkg"
    assert main("elevation", "GEBCO", argv=["--nc", str(desc_nc), "--shp", str(desc), *box]) == 0

    a = gpd.read_file(asc)
    d = gpd.read_file(desc)
    assert set(a.Depth.unique()) == set(d.Depth.unique())
    assert d.geometry.is_valid.all()
    for depth in a.Depth.unique():
        la = a[a.Depth == depth].geometry.length.sum()
        ld = d[d.Depth == depth].geometry.length.sum()
        assert la == pytest.approx(ld, rel=1e-9)


@pytest.mark.skipif(not ETOPO_SUBSET.exists(), reason="ETOPO fixture missing")
def test_real_etopo_subset_via_generality_flags(tmp_path):
    # Real ETOPO grid uses altitude / latitude / longitude, exercising the
    # --variable / --latname / --lonname options on real data.
    import geopandas as gpd

    from isobaths import main

    out = tmp_path / "e.gpkg"
    rc = main(
        "Band1",
        "NOAA",
        argv=[
            "--nc",
            str(ETOPO_SUBSET),
            "--shp",
            str(out),
            "--variable",
            "altitude",
            "--latname",
            "latitude",
            "--lonname",
            "longitude",
            "--contour",
            "100,500,1000,2000",
        ],
    )
    assert rc == 0
    e = gpd.read_file(out)
    assert not e.empty
    assert e.geometry.is_valid.all()
    assert e.crs.to_epsg() == 4326


# --------------------------------------------------------------------------- #
# End-to-end through the CLI driver
# --------------------------------------------------------------------------- #


def _write_fixture(path, varname, lon, lat, elev, descending=False):
    if descending:
        lat = lat[::-1]
        elev = elev[::-1, :]
    ds = xr.Dataset({varname: (("lat", "lon"), elev)}, coords={"lat": lat, "lon": lon})
    ds.to_netcdf(path)


def test_end_to_end_gebco_and_noaa_agree(tmp_path, bowl):
    import geopandas as gpd

    from isobaths import main

    lon, lat, elev = bowl

    gebco = tmp_path / "gebco.nc"
    noaa = tmp_path / "noaa.nc"
    _write_fixture(gebco, "elevation", lon, lat, elev)
    _write_fixture(noaa, "Band1", lon, lat, elev, descending=True)

    box = [
        "--latmin",
        "5",
        "--latmax",
        "20",
        "--lonmin",
        "105",
        "--lonmax",
        "118",
        "--contour",
        "200,500,1000",
    ]

    g_shp = tmp_path / "g.shp"
    rc = main("elevation", "GEBCO", argv=["--nc", str(gebco), "--shp", str(g_shp), *box])
    assert rc == 0
    g = gpd.read_file(g_shp)
    assert not g.empty and set(g.Depth.unique()).issubset({200, 500, 1000})

    # NOAA file has descending latitude; must still produce the same contours.
    n_shp = tmp_path / "n.shp"
    rc = main("Band1", "NOAA", argv=["--nc", str(noaa), "--shp", str(n_shp), *box])
    assert rc == 0
    n = gpd.read_file(n_shp)
    assert not n.empty
    assert set(n.Depth.unique()) == set(g.Depth.unique())


def test_end_to_end_overlapping_contours_do_not_crash(tmp_path, bowl):
    # 200 appears in both --contour lists; must be de-duplicated, not crash.
    import geopandas as gpd

    from isobaths import main

    lon, lat, elev = bowl
    gebco = tmp_path / "gebco.nc"
    _write_fixture(gebco, "elevation", lon, lat, elev)
    rc = main(
        "elevation",
        "GEBCO",
        argv=[
            "--nc",
            str(gebco),
            "--shp",
            str(tmp_path / "o.shp"),
            "--contour",
            "0,200",
            "--contour",
            "200,500",
        ],
    )
    assert rc == 0
    assert not gpd.read_file(tmp_path / "o.shp").empty


def test_end_to_end_missing_variable_reports_cleanly(tmp_path, bowl, capsys):
    from isobaths import main

    lon, lat, elev = bowl
    gebco = tmp_path / "gebco.nc"
    _write_fixture(gebco, "elevation", lon, lat, elev)
    # NOAA wrapper looks for Band1, which isn't in this GEBCO-style file.
    rc = main("Band1", "NOAA", argv=["--nc", str(gebco), "--shp", str(tmp_path / "x.shp")])
    assert rc != 0
