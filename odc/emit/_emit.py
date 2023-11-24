"""
EMIT helper functions.
"""

import os
import sys
import requests
from cachetools import cached
from pathlib import Path
from typing import Hashable, Any

from odc.geo.math import affine_from_pts, quasi_random_r2
from odc.geo import xy_, wh_
from odc.geo.geobox import GeoBox
from odc.geo.gcp import GCPMapping, GCPGeoBox
from odc.geo import geom
from affine import Affine

import numpy as np

_creds_cache: dict[Hashable, dict[str, Any]] = {}


def earthdata_token(tk=None):
    if tk is not None:
        return tk

    if (tk := os.environ.get("EARTHDATA_TOKEN", None)) is None:
        tk_file = Path.home() / ".safe" / "earth-data.tk"

        if tk_file.exists():
            print(f"Reading from: {tk_file}", file=sys.stderr)
            with tk_file.open("rt", encoding="utf8") as src:
                tk = src.read().strip()

    if tk is None:
        raise RuntimeError(f"please set EARTHDATA_TOKEN= or create: {tk_file}")

    return tk


@cached(_creds_cache)
def fetch_s3_creds(tk=None):
    tk = earthdata_token(tk)
    return requests.get(
        "https://data.lpdaac.earthdatacloud.nasa.gov/s3credentials",
        headers={"Authorization": f"Bearer {tk}"},
        timeout=20,
    ).json()


def gxy(gg):
    return np.asarray(gg.json["coordinates"])


def parse_emit_orbit(item):
    if isinstance(item, str):
        _id = item
    else:
        _id = item.id

    return int(_id.split("_")[-2])


def gbox_from_points(pix, wld, shape):
    crs = wld.crs
    _pix = [xy_(*g.points[0]) for g in pix.geoms]
    _wld = [xy_(*g.points[0]) for g in wld.geoms]
    A = affine_from_pts(_pix, _wld)
    gbox = GeoBox(shape, A, crs)
    return gbox


def gbox_from_pix_lonlat(lon, lat, *, nsamples=100, crs=None, approx=False):
    assert lon.shape == lat.shape

    ix, iy = quasi_random_r2(nsamples, lon.shape).astype("int32").T
    wld = geom.multipoint([(x, y) for x, y in zip(lon[iy, ix], lat[iy, ix])], 4326)
    pix = geom.multipoint([(x + 0.5, y + 0.5) for x, y in zip(ix, iy)], None)

    if crs is not None:
        wld = wld.to_crs(crs)

    if approx:
        return gbox_from_points(pix, wld, lon.shape)

    return GCPGeoBox(lon.shape, GCPMapping(pix, wld))


def ortho_gbox(zarr_meta):
    h, w = zarr_meta["location/glt_x/.zarray"]["shape"]
    tx, sx, _, ty, _, sy = zarr_meta[".zattrs"]["geotransform"]
    return GeoBox(wh_(w, h), Affine(sx, 0, tx, 0, sy, ty), 4326)


def snap_to(x, y, off=0.5):
    def op(x):
        return [int(_x) + off for _x in x]

    return op(x), op(y)


def sample_error_0(gbox, lon, lat, nsamples):
    pix_ = gbox.qr2sample(nsamples).transform(lambda x, y: snap_to(x, y, 0))

    iy, ix = gxy(pix_).astype(int).T
    ww = geom.multipoint([(x, y) for x, y in zip(lon[ix, iy], lat[ix, iy])], 4326)

    pix_c = pix_.transform(lambda x, y: snap_to(x, y, 0.5))

    ee = gxy(pix_c) - gxy(gbox.project(ww))
    pix_error = np.sqrt((ee**2).sum(axis=1))

    return pix_c, ww, pix_error, ee


def sample_error(xx, nsamples):
    gbox = xx.odc.geobox
    lon = xx.lon.data
    lat = xx.lat.data

    pix_ = gbox.qr2sample(nsamples).transform(lambda x, y: snap_to(x, y, 0))

    iy, ix = gxy(pix_).astype(int).T
    ww = geom.multipoint([(x, y) for x, y in zip(lon[ix, iy], lat[ix, iy])], 4326)

    pix_c = pix_.transform(lambda x, y: snap_to(x, y, 0.5))

    ee = gxy(pix_c) - gxy(gbox.project(ww))
    pix_error = np.sqrt((ee**2).sum(axis=1))

    return pix_c, ww, pix_error, ee
