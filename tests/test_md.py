import pytest
from pystac.item import Item
from utils._md import cmr_to_stac
from utils.vendor.eosdis_store.dmrpp import to_zarr
from utils.emit import to_zarr_spec
from pathlib import Path
import json

# pylint: disable=redefined-outer-name


@pytest.fixture
def data_dir():
    yield Path(__file__).parent / "data"


@pytest.fixture
def cmr_sample(data_dir):
    path = data_dir / "emit_l2a_rfl_sample.cmr.json"
    with open(path, "rt", encoding="utf8") as f:
        doc = json.load(f)
    yield doc


@pytest.fixture
def dmrpp_sample(data_dir):
    path = data_dir / "emit_l2a_rfl_sample.dmrpp"
    with open(path, "rt", encoding="utf8") as f:
        doc = f.read()
    yield doc


def test_cmr(cmr_sample):
    dd = cmr_to_stac(cmr_sample)
    assert "id" in dd
    item = Item.from_dict(dd)

    assert len(item.assets) > 0
    assert item.datetime is not None


def test_dmrpp(dmrpp_sample):
    zz = to_zarr(dmrpp_sample)
    assert isinstance(zz, dict)
    assert "reflectance/.zarray" in zz
    assert "reflectance/.zchunkstore" in zz
    assert list(zz["reflectance/.zchunkstore"]) == ["0.0.0"]
    assert list(zz["location/lon/.zchunkstore"]) == ["0.0"]


def test_to_zarr_spec(dmrpp_sample):
    url = "s3://fake/dummy.nc"

    spec = to_zarr_spec(dmrpp_sample, url)
    assert list(spec) == ["version", "refs"]
    assert "reflectance/0.0.0" in spec["refs"]
    xx = spec["refs"]["reflectance/0.0.0"]
    assert isinstance(xx, tuple)
    assert len(xx) == 3
    assert xx[0] == url
    assert isinstance(xx[1], int)
    assert isinstance(xx[2], int)