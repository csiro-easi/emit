"""
EMIT error analysis functions.
"""

from types import SimpleNamespace

import numpy as np
import xarray as xr
from odc.geo import geom


def gxy(gg):
    return np.asarray(gg.json["coordinates"])


def snap_to(x, y, off=0.5):
    def op(x):
        return [int(_x) + off for _x in x]

    return op(x), op(y)


def sample_error_0(gbox, lon, lat, nsamples):
    pix_ = gbox.qr2sample(nsamples).transform(lambda x, y: snap_to(x, y, 0))

    iy, ix = gxy(pix_).astype(int).T
    ww = geom.multipoint(list(zip(lon[ix, iy], lat[ix, iy])), 4326)

    pix_c = pix_.transform(lambda x, y: snap_to(x, y, 0.5))

    ee = gxy(pix_c) - gxy(gbox.project(ww))
    pix_error = np.sqrt((ee**2).sum(axis=1))

    return pix_c, ww, pix_error, ee


def sample_error(xx: xr.Dataset, nsamples: int) -> SimpleNamespace:
    gbox = xx.odc.geobox
    lon = xx.lon.data
    lat = xx.lat.data

    pix_ = gbox.qr2sample(nsamples).transform(lambda x, y: snap_to(x, y, 0))
    iy, ix = gxy(pix_).astype(int).T
    pts_p = pix_.transform(lambda x, y: snap_to(x, y, 0.5))

    pts_w = geom.multipoint(list(zip(lon[ix, iy], lat[ix, iy])), 4326)

    ee = gxy(pts_p) - gxy(gbox.project(pts_w))
    pix_error = np.sqrt((ee**2).sum(axis=1))

    return SimpleNamespace(pts_p=pts_p, pts_w=pts_w, pix_error=pix_error, ee=ee)


def mk_error_plot(
    xx: xr.Dataset,
    nsamples: int = 100,
    max_err_axis: float = -1,
    msg: str = "",
) -> SimpleNamespace:
    # pylint: disable=import-outside-toplevel

    import seaborn as sns
    from matplotlib import pyplot as plt

    rr = sample_error(xx, nsamples)

    fig, axd = plt.subplot_mosaic(
        [
            ["A", "A", "A", "B", "B"],
            ["A", "A", "A", "B", "B"],
            ["C", "C", "C", "C", "C"],
        ],
        figsize=(8, 8),
    )
    rr.fig = fig
    rr.axd = axd

    info = []
    if epsg := xx.odc.crs.epsg:
        info.append(f"epsg:{epsg}")

    info.append(f"avg:{rr.pix_error.mean():.3f}px")
    if msg:
        info.append(msg)
    info = " ".join(info)

    fig.suptitle(f"Pixel Registration Error, {info}")

    sns.scatterplot(x=rr.ee.T[0], y=rr.ee.T[1], size=rr.pix_error, ax=axd["A"])
    if max_err_axis > 0:
        b = max_err_axis
    else:
        b = max(map(abs, axd["A"].axis()))  # type: ignore

    axd["A"].axis((-b, b, -b, b))
    axd["A"].axvline(0, color="k", linewidth=0.3)
    axd["A"].axhline(0, color="k", linewidth=0.3)

    X, Y = gxy(rr.pts_p).T
    sns.heatmap(
        xx.reflectance.isel(band=100),
        cmap="bone",
        alpha=0.7,
        square=True,
        cbar=False,
        xticklabels=False,
        yticklabels=False,
        ax=axd["B"],
    )
    with plt.rc_context({"legend.loc": "lower right"}):
        sns.scatterplot(
            x=X,
            y=Y,
            size=rr.pix_error,
            color="c",
            alpha=0.5,
            ax=axd["B"],
        )

    axd["C"].axvline(rr.pix_error.mean(), color="y")
    sns.kdeplot(rr.pix_error, ax=axd["C"], clip=(0, b * 100))
    *_, maxy = axd["C"].axis()
    axd["C"].axis((0, b, 0, maxy))
    fig.tight_layout()
    return rr
