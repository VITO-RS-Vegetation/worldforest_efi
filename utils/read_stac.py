from pathlib import Path

import rioxarray
import xarray as xr
from pystac_client import Client
from yarl import URL


def get_local_path(item_collection):
    all_local_paths = []
    for _item in item_collection:
        try:
            local_path = Path(
                URL(
                    _item
                    .assets["MAP"]
                    .extra_fields["alternate"]["local"]["href"]
                ).path
            )
            if local_path.exists():
                all_local_paths.append(local_path)
        except (KeyError, AttributeError) as e:
            print(e)
            continue
    return all_local_paths
    


def get_data_from_files(all_paths, bbox_4326):
    data_arrays = []
    for path in all_paths:
        try:
            da = rioxarray.open_rasterio(path)
            # Clip the data to the input bbox (assumes bbox_4326 is [minx, miny, maxx, maxy])
            da_clipped = da.rio.clip_box(
                minx=bbox_4326[0],
                miny=bbox_4326[1],
                maxx=bbox_4326[2],
                maxy=bbox_4326[3],
                crs="EPSG:4326",
            )
            data_arrays.append(da_clipped)
        except Exception as e:
            print(f"Failed to open or clip {path}: {e}")
    # Merge all clipped arrays spatially
    if len(data_arrays) > 1:
        merged = xr.merge(data_arrays)
    elif len(data_arrays) == 1:
        merged= data_arrays[0]
    else:
        merged = None
    return merged


def get_stac_client(collection, bbox_4326, temporal_extent=None):
    # "lcfm-lcm-10"
    client = Client.open("https://stac.terrascope.be")
    collection = client.get_collection(collection)
    search = client.search(
        collections=collection.id,
        datetime=temporal_extent,
        bbox=bbox_4326,
    )
    item_collection = search.item_collection()
    all_paths = get_local_path(item_collection)
    # read data of the bbox from local path
    return get_data_from_files(all_paths, bbox_4326)
