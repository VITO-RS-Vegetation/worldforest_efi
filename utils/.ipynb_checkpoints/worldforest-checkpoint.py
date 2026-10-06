"""
This module provides the data-loading and plotting building blocks for the tool.
It defines `SpatialBounds` for handling/transforming plot extents, `ClassMap` for loading,
classifying and plotting raster layers (VRT/tiff), and helpers to compute pixel statistics
and disturbance summaries.
"""

import copy
import math
from typing import Any, Dict, Optional

import geopandas as gpd
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import parameters
import rasterio
import xarray as xr
from matplotlib import colors as mcolors
from matplotlib import pyplot as plt
from pyproj import Transformer
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from shapely.geometry import box


def _overlay_rectangle(ax, extent, edgecolor="black", facecolor="none", linewidth=1, label=None, zorder=4):
    """
    Overlay a rectangle on the axes given extent.
    extent: dict with keys 'west', 'south', 'east', 'north'
    """
    width = extent["east"] - extent["west"]
    height = extent["north"] - extent["south"]
    rect = mpatches.Rectangle(
        (extent["west"], extent["south"]),
        width,
        height,
        edgecolor=edgecolor,
        facecolor=facecolor,
        linewidth=linewidth,
        label=label,
        zorder=zorder,
    )
    ax.add_patch(rect)
    if label:
        ax.text(
            0.99, 0.99, label,
            transform=ax.transAxes,
            ha="right", va="top",
            fontsize=10,
            color="black",
            bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=2)
        )


class SpatialBounds:
    """
    Handles spatial bounds from either a GeoSeries or a bounds dict.
    Provides both original and latlon dicts.
    """

    def __init__(
        self,
        geometry: Optional[gpd.GeoSeries] = None,
        bounds: Optional[Dict[str, Any]] = None,
        margin_km: float = 1.0,
    ):
        self.margin_km = margin_km
        if geometry is not None:
            minx, miny, maxx, maxy = geometry.total_bounds
            crs = geometry.crs
            epsg = crs.to_epsg() if crs else 4326
            self.xy = {
                "west": minx,
                "south": miny,
                "east": maxx,
                "north": maxy,
                "epsg": epsg,
            }
            self.latlon = self._to_latlon(self.xy, crs)
        elif bounds is not None:
            self.xy = copy.deepcopy(bounds)
            self.latlon = self._to_latlon(self.xy, f"EPSG:{bounds['epsg']}")
        else:
            raise ValueError("Must provide either geometry or bounds.")

    def _to_latlon(self, bounds: Dict[str, Any], crs) -> Dict[str, Any]:
        """Transform bounds to EPSG:4326 if needed."""
        if bounds["epsg"] == 4326:
            return copy.deepcopy(bounds)
        gdf = gpd.GeoSeries(
            [box(bounds["west"], bounds["south"], bounds["east"], bounds["north"])],
            crs=crs,
        )
        gdf_ll = gdf.to_crs(epsg=4326)
        lon_min, lat_min, lon_max, lat_max = gdf_ll.total_bounds
        return {
            "west": lon_min,
            "south": lat_min,
            "east": lon_max,
            "north": lat_max,
            "epsg": 4326,
        }

    def __repr__(self):
        return f"SpatialBounds(original={self.xy}, latlon={self.latlon})"

    @staticmethod
    def expand_bounds_km(bounds: Dict[str, Any], margin_km: float) -> Dict[str, Any]:
        """
        Expand bounds by a fixed distance in kilometers on all sides.
        """
        if bounds["epsg"] == 4326:
            center_lat = (bounds["south"] + bounds["north"]) / 2
            dlat = margin_km / 110.574
            dlon = margin_km / max(111.320 * math.cos(math.radians(center_lat)), 1e-6)
        else:
            dlat = dlon = margin_km * 1000.0
        return {
            "west": bounds["west"] - dlon,
            "south": bounds["south"] - dlat,
            "east": bounds["east"] + dlon,
            "north": bounds["north"] + dlat,
            "epsg": bounds["epsg"],
        }

    @property
    def expanded_xy(self):
        """
        Returns bounds expanded by a default margin (e.g., 1 km).
        """
        return self.expand_bounds_km(self.xy, self.margin_km)

    @property
    def expanded_latlon(self):
        """
        Returns the expanded bounds transformed to EPSG:4326.
        Expands in the original CRS first, then reprojects (as done at initialization).
        """
        return self._to_latlon(self.expanded_xy, f"EPSG:{self.xy['epsg']}")
    
    

class ClassMap:
    def __init__(self, name, filename, years=None, class_dict=None, class_colors=None):
        self.name = name
        if years is None:
            self.filename = filename
        else:
            self.filename = {year: filename.format(year=year) for year in years}
        self.cmap = None
        self.norm = None
        self.legend_handles = None
        if class_dict is not None:
            self.class_dict = class_dict
            self.class_colors = self._normalize_colors(class_colors)
            self.class_ids = sorted(class_dict.keys())
            self.class_names = [class_dict[c] for c in self.class_ids]
            self.cmap = self._build_colormap()
            self.norm = self._build_norm()
            # Class legend (colored patches) for genus map
            self.legend_handles = [
                mpatches.Patch(
                    color=self.class_colors.get(class_id),
                    label=self.class_dict.get(class_id, f"Unknown ({class_id})"),
                )
                for class_id in self.class_ids
            ]
        self.load_data = self._select_loader()

    def _normalize_colors(self, class_colors):
        norm_colors = {}
        for k, v in class_colors.items():
            if isinstance(v, str):
                rgb = mcolors.to_rgb(v)
            else:
                rgb = tuple(channel / 255.0 for channel in v)
            norm_colors[k] = rgb
        return norm_colors

    def _build_colormap(self):
        color_list = [self.class_colors[c] for c in self.class_ids]
        return mcolors.ListedColormap(color_list)

    def _build_norm(self):
        bounds = np.array(self.class_ids + [self.class_ids[-1] + 1]) - 0.5
        return mcolors.BoundaryNorm(bounds, self.cmap.N)

    def get_legend_handles(self):
        """Return the legend handles built in __init__ (colored patch per class)."""
        return self.legend_handles

    def plot(self, data, ax=None, overlay_extent=None, overlay_label=None, title=None, **kwargs):
        """
        Plot the data using matplotlib, colored/classified according to this ClassMap.
        data: xarray DataArray
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 5), dpi=150)
        else:
            fig = ax.get_figure()

        if self.norm:
            im = ax.pcolormesh(data.lon, data.lat, data.values, cmap=self.cmap, norm=self.norm)
        else:
            im = ax.pcolormesh(data.lon, data.lat, data.values, cmap=self.cmap, **kwargs)
        ax.set_title(title if title is not None else self.name)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        if self.legend_handles is not None:
            # EFI plot legend on top of the figure, separate from the class legend below
            ax.legend(handles=self.legend_handles, loc="upper left",
                      bbox_to_anchor=(1.01, 1), fontsize=8, framealpha=0.9)
        else:
            cbar = fig.colorbar(im, ax=ax, orientation="vertical", fraction=0.046, pad=0.04)
            cbar.set_label(data.attrs.get("units", "m"), rotation=270, labelpad=15)
        if overlay_extent:
            _overlay_rectangle(ax, overlay_extent, label=overlay_label)
        return fig

    def __repr__(self):
        return (
            f"ClassColorMap(filename={self.filename!r}, "
            f"class_ids={self.class_ids}, "
            f"class_names={self.class_names})"
        )

    def get_data_from_raster(
            self, spatial_extent: dict, masked_array=False, year: Optional[int] = None
    ) -> xr.DataArray:
        """
        Extract data from the raster file for a given spatial extent.

        Args:
            spatial_extent (dict): Spatial extent defined as a dictionary with the following keys:
                - "west" (float): Western boundary (longitude or x-coordinate).
                - "south" (float): Southern boundary (latitude or y-coordinate).
                - "east" (float): Eastern boundary (longitude or x-coordinate).
                - "north" (float): Northern boundary (latitude or y-coordinate).
                - "epsg" (int): EPSG code of the spatial extent's coordinate reference system.

        Returns:
            xr.DataArray: An xarray DataArray containing the extracted data, with coordinates and attributes.
        """
        if year is not None:
            filename = self.filename.get(year)
        else:
            filename = self.filename
        # print(f"Loading data from raster: {filename} for spatial extent: {spatial_extent}")
        with rasterio.open(filename, masked=True) as src:
            # Convert spatial extent to the raster's CRS if necessary
            if src.crs.to_epsg() != spatial_extent["epsg"]:
                bounds = transform_bounds(
                    spatial_extent["epsg"],
                    src.crs,
                    spatial_extent["west"],
                    spatial_extent["south"],
                    spatial_extent["east"],
                    spatial_extent["north"],
                )
            else:
                bounds = (
                    spatial_extent["west"],
                    spatial_extent["south"],
                    spatial_extent["east"],
                    spatial_extent["north"],
                )

            # Ensure the bounds are within the raster's extent
            raster_bounds = src.bounds
            if (
                bounds[0] < raster_bounds.left
                or bounds[2] > raster_bounds.right
                or bounds[1] < raster_bounds.bottom
                or bounds[3] > raster_bounds.top
            ):
                raise ValueError(
                    "The specified bounds are outside the raster's extent."
                )

            # Read the data for the specified bounds
            window = from_bounds(*bounds, transform=src.transform)
            data = src.read(1, window=window, masked=True)  # Read the first band
            if masked_array:
                return data  # Return as a masked array if requested
            # scale the data based on the raster's metadata (e.g., scale factor, offset) if necessary
            # print(f"src.scales: {src.scales}, src.offsets: {src.offsets}")
            if src.scales[0] is not None:
                data = data * src.scales[0]
            if src.offsets[0] is not None:
                data = data + src.offsets[0]
            # units of the data can be obtained from src.tags() if necessary
            units = src.tags().get("units", "")

            # Build coordinates from the actual raster window shape
            window_transform = src.window_transform(window)
            x = (
                window_transform.c
                + (np.arange(data.shape[1], dtype=float) + 0.5) * window_transform.a
            )
            y = (
                window_transform.f
                + (np.arange(data.shape[0], dtype=float) + 0.5) * window_transform.e
            )

            # Build lon/lat from x/y
            src_crs = src.crs
            src_epsg = src_crs.to_epsg() if src_crs is not None else None

            xx, yy = np.meshgrid(x, y)
            if src_epsg == 4326:
                # CRS already geographic: lon=x, lat=y
                lon2d, lat2d = xx, yy
            else:
                # Reproject from raster CRS -> EPSG:4326
                transformer = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
                lon2d, lat2d = transformer.transform(xx, yy)

        data_arr = xr.DataArray(
            data,
            coords={
                "y": y,
                "x": x,
                # 2D geodetic coordinates aligned to (y, x) grid
                "lat": (("y", "x"), lat2d),
                "lon": (("y", "x"), lon2d),
            },
            dims=("y", "x"),
        )

        data_arr.attrs["units"] = units
        # rioxarray geospatial metadata (preferred)
        if src_crs is not None:
            data_arr = data_arr.rio.set_spatial_dims(
                x_dim="x", y_dim="y", inplace=False
            )
            data_arr = data_arr.rio.write_crs(src_crs, inplace=False)
            # Optional but useful for some workflows:
            data_arr = data_arr.rio.write_coordinate_system(inplace=False)

        # Optional convenience attrs
        if src_epsg is not None:
            data_arr.attrs["epsg"] = int(src_epsg)

        return data_arr

    def get_data_from_stac(self, spatial_extent):
        # ... (your STAC loading code here)
        pass

    def _select_loader(self):
        """
        Selects the appropriate data loading function based on the filename.
        """
        if isinstance(self.filename, dict):
            return self.get_data_from_raster  # For year-based filenames, use raster loader
        elif self.filename.endswith(".vrt") or self.filename.endswith(".tif"):
            return self.get_data_from_raster
        elif self.filename.startswith("stac://") or self.filename.endswith(".json"):
            return self.get_data_from_stac
        else:
            raise ValueError(f"Unknown data source for filename: {self.filename}")



    
genus_map_class = ClassMap(**parameters.GENUS_MAP)

canopy_height_class = ClassMap(**parameters.CANOPY_HEIGHT)
canopy_height_class.cmap = "viridis"

foliage_height_diversity_class = ClassMap(**parameters.FOLIAGE_HEIGHT_DIVERSITY)
foliage_height_diversity_class.cmap = "plasma"

land_cover = ClassMap(**parameters.LANDCOVER)

years = range(1985, 2025)
annual_disturbance_class = ClassMap(**parameters.ANNUAL_DISTURBANCE, years=years)
disturbance_agent_class = ClassMap(**parameters.DISTURBANCE_AGENT, years=years)

latest_disturbance_class = ClassMap(**parameters.LATEST_DISTURBANCE)
latest_disturbance_class.cmap = "Spectral_r"
agent_aggregated_class = ClassMap(**parameters.AGENT_AGGREGATED)



def get_stats(data, layer_name, extent_name, cover_data=None, debug=False):
    if cover_data is not None:
        tree_mask = np.ma.getmaskarray(cover_data) | (cover_data <= 0)
        data = np.ma.array(data, mask=np.ma.getmaskarray(data) | tree_mask)

    valid = data.to_masked_array().compressed()  # Flattened array of valid pixels

    if valid.size == 0:
        if debug:
            return pd.DataFrame([{
                "layer_name": layer_name,
                "extent_name": extent_name,
                "n_valid_pixels": 0,
                "min": np.nan,
                "p50": np.nan,
                "p95": np.nan,
                "p99": np.nan,
                "max": np.nan,
                "mean": np.nan
            }])
        else:
            return pd.DataFrame([{
                "layer_name": layer_name,
                "extent_name": extent_name,
                "mean": np.nan
            }])

    p50, p95, p99 = np.percentile(valid, [50, 95, 99])
    result = {
        "layer_name": layer_name,
        "extent_name": extent_name,
        "n_valid_pixels": valid.size,
        "min": valid.min(),
        "p50": p50,
        "p95": p95,
        "p99": p99,
        "max": valid.max(),
        "mean": valid.mean()
    }
    if debug:
        return pd.DataFrame([result])
    else:
        return pd.DataFrame([{
            "layer_name": layer_name,
            "extent_name": extent_name,
            "mean": valid.mean()
        }])


def compute_disturbance_stats(years, plot_spatial):
    """
    Compute disturbance statistics for a list of years.
    Only returns years with at least one disturbed pixel.
    """
    agent_names = {
            1: "Wind/bark beetle complex (pixels)",
            2: "Fire (pixels)",
            3: "Harvest (pixels)",
            4: "Mixed agent (pixels)",
        }
    summary_data = []
    for year in years:
        disturbance_data = annual_disturbance_class.load_data(plot_spatial.expanded_xy, year=year)
        agent_data = disturbance_agent_class.load_data(plot_spatial.expanded_xy, year=year)
        
        disturbed_pixels = int(np.sum(disturbance_data.values > 0))
        total_pixels = int(disturbance_data.size)
        disturbed_pct = (disturbed_pixels / total_pixels * 100) if total_pixels > 0 else 0.0
        
        # Only keep years with at least one disturbed pixel
        if disturbed_pixels == 0:
            continue
        
        agent_counts = {}
        unique_agents = np.unique(agent_data.values[disturbance_data.values > 0])
        for agent in unique_agents:
            count = int(np.sum((agent_data.values == agent) & (disturbance_data.values > 0)))
            agent_id = int(agent)
            agent_counts[agent_names.get(agent_id, f"Agent_{agent_id}")] = count
        
        row = {
            "Year": year,
            "Total_Pixels": total_pixels,
            "Disturbed_Pixels": disturbed_pixels,
            "Disturbed_%": disturbed_pct,
        }
        row.update(agent_counts)
        summary_data.append(row)
    summary_df = pd.DataFrame(summary_data)
    return summary_df


def class_distribution_percent(masked_data):
    """
    Compute the percentage distribution of classes in a masked array.
    Returns a DataFrame with columns 'class' and 'percent'.
    """
    valid = masked_data.compressed()
    if valid.size == 0:
        return pd.DataFrame(columns=["class", "percent"])
    classes, counts = np.unique(valid, return_counts=True)
    total = counts.sum()
    df = pd.DataFrame({
        "class": classes.astype(int),
        "percent": counts / total * 100.0
    })
    return df.sort_values("class").reset_index(drop=True)
