"""Map layers: configuration, data loading (raster or STAC) and class styling."""

from typing import Optional

import matplotlib.patches as mpatches
import numpy as np
import rasterio
import rioxarray  # noqa: F401  (registers the ``.rio`` accessor)
import xarray as xr
from matplotlib import colors as mcolors
from pyproj import Transformer
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

from . import plotting, read_stac
from .spatial import Bounds, SpatialBounds


def _extent_to_crs(spatial_extent: Bounds, dst_crs: rasterio.crs.CRS) -> tuple:
    """Return (west, south, east, north) of the extent expressed in ``dst_crs``."""
    bounds = SpatialBounds.to_bbox(spatial_extent)
    if dst_crs.to_epsg() == spatial_extent["epsg"]:
        return tuple(bounds)
    return transform_bounds(f"EPSG:{spatial_extent['epsg']}", dst_crs, *bounds)


def _build_dataarray(data, x, y, crs, units: str = "") -> xr.DataArray:
    """Wrap a 2D array into a DataArray with x/y, 2D lon/lat coords and rio CRS metadata."""
    epsg = crs.to_epsg() if crs is not None else None
    xx, yy = np.meshgrid(x, y)
    if epsg == 4326:
        lon2d, lat2d = xx, yy
    else:
        transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
        lon2d, lat2d = transformer.transform(xx, yy)

    data_arr = xr.DataArray(
        data,
        coords={
            "y": y,
            "x": x,
            "lat": (("y", "x"), lat2d),
            "lon": (("y", "x"), lon2d),
        },
        dims=("y", "x"),
        attrs={"units": units},
    )
    if crs is not None:
        data_arr = data_arr.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=False)
        data_arr = data_arr.rio.write_crs(crs, inplace=False)
        data_arr = data_arr.rio.write_coordinate_system(inplace=False)
    if epsg is not None:
        data_arr.attrs["epsg"] = int(epsg)
    return data_arr


class ClassMap:
    """
    A map layer backed by either a local raster (``filename``) or a STAC
    collection (``collection``). Optionally classified via ``class_dict`` /
    ``class_colors``, which drive the colormap, norm and legend used when plotting.

    ``load_data(spatial_extent, masked_array=False, **kw)`` dispatches to the
    appropriate loader (``get_data_from_raster`` or ``get_data_from_stac``).
    """

    def __init__(
        self,
        name,
        filename=None,
        collection=None,
        years=None,
        class_dict=None,
        class_colors=None,
        cmap=None,
        units="",
    ):
        if (filename is None) == (collection is None):
            raise ValueError("Provide exactly one of 'filename' or 'collection'.")
        self.name = name
        self.collection = collection
        if filename is not None and years is not None:
            self.filename = {year: filename.format(year=year) for year in years}
        else:
            self.filename = filename

        self.cmap = cmap
        self.units = units
        self.norm = None
        self.legend_handles = None
        self.class_dict = class_dict
        self.class_colors = None
        self.class_ids = None
        self.class_names = None
        if class_dict is not None:
            self.class_colors = self._normalize_colors(class_colors)
            self.class_ids = sorted(class_dict.keys())
            self.class_names = [class_dict[c] for c in self.class_ids]
            self.cmap = mcolors.ListedColormap([self.class_colors[c] for c in self.class_ids])
            bounds = np.array(self.class_ids + [self.class_ids[-1] + 1]) - 0.5
            self.norm = mcolors.BoundaryNorm(bounds, self.cmap.N)
            self.legend_handles = [
                mpatches.Patch(
                    color=self.class_colors.get(class_id),
                    label=class_dict.get(class_id, f"Unknown ({class_id})"),
                )
                for class_id in self.class_ids
            ]

        self.load_data = self.get_data_from_stac if collection is not None else self.get_data_from_raster

    @staticmethod
    def _normalize_colors(class_colors):
        """Accept hex strings or 0-255 RGB tuples; return 0-1 RGB tuples."""
        return {
            k: mcolors.to_rgb(v) if isinstance(v, str) else tuple(c / 255.0 for c in v)
            for k, v in class_colors.items()
        }

    def get_legend_handles(self):
        """Colored patch per class, or None for continuous layers."""
        return self.legend_handles

    def plot(self, data, ax=None, overlay_extent=None, overlay_label=None, title=None, **kwargs):
        """Plot ``data`` styled by this layer. See :func:`utils.plotting.plot_map`."""
        return plotting.plot_map(
            data, self, ax=ax, overlay_extent=overlay_extent,
            overlay_label=overlay_label, title=title, **kwargs
        )

    def get_data_from_raster(
        self, spatial_extent: Bounds, masked_array=False, year: Optional[int] = None
    ):
        """
        Read the first band of the raster for a spatial extent.

        spatial_extent: dict with 'west', 'south', 'east', 'north' and 'epsg'.
        Returns a masked array if ``masked_array`` is True, else a DataArray with
        x/y and 2D lon/lat coordinates, scaled by the raster's scale/offset.
        """
        filename = self.filename.get(year) if year is not None else self.filename
        with rasterio.open(filename, masked=True) as src:
            bounds = _extent_to_crs(spatial_extent, src.crs)
            rb = src.bounds
            if bounds[0] < rb.left or bounds[2] > rb.right or bounds[1] < rb.bottom or bounds[3] > rb.top:
                raise ValueError("The specified bounds are outside the raster's extent.")

            window = from_bounds(*bounds, transform=src.transform)
            data = src.read(1, window=window, masked=True)
            if masked_array:
                return data

            if src.scales[0] is not None:
                data = data * src.scales[0]
            if src.offsets[0] is not None:
                data = data + src.offsets[0]
            units = src.tags().get("units", "")

            wt = src.window_transform(window)
            x = wt.c + (np.arange(data.shape[1], dtype=float) + 0.5) * wt.a
            y = wt.f + (np.arange(data.shape[0], dtype=float) + 0.5) * wt.e
            crs = src.crs

        return _build_dataarray(data, x, y, crs, units)

    def get_data_from_stac(
        self, spatial_extent: Bounds, masked_array=False, temporal_extent=None
    ):
        """
        Load the STAC collection for a spatial extent via :mod:`utils.read_stac`.

        spatial_extent: dict with 'west', 'south', 'east', 'north' and 'epsg'.
        temporal_extent: optional pystac-client datetime filter (e.g. "2020-01-01/2020-12-31").
        Returns a masked array if ``masked_array`` is True, else a DataArray with
        x/y and 2D lon/lat coordinates (same layout as ``get_data_from_raster``).
        """
        bbox_4326 = list(_extent_to_crs(spatial_extent, rasterio.crs.CRS.from_epsg(4326)))
        da = read_stac.get_stac_client(self.collection, bbox_4326, temporal_extent)
        if da is None:
            raise ValueError(
                f"No STAC data found for collection '{self.collection}' and bbox {bbox_4326}"
            )
        if "band" in da.dims:
            da = da.isel(band=0)

        nodata = da.rio.nodata if da.rio.nodata is not None else da.rio.encoded_nodata
        values = da.values
        data = np.ma.masked_equal(values, nodata) if nodata is not None else np.ma.masked_invalid(values)
        if masked_array:
            return data

        return _build_dataarray(data, da.x.values, da.y.values, da.rio.crs, da.attrs.get("units", ""))

    def __repr__(self):
        source = f"collection={self.collection!r}" if self.collection else f"filename={self.filename!r}"
        return f"ClassMap(name={self.name!r}, {source}, class_ids={self.class_ids})"
