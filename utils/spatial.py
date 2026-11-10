"""Spatial extent handling for EFI plots (original CRS and EPSG:4326 bounds)."""

import copy
import math
from typing import Any

import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import box

PLOT_SIZE_M = 100.0
PLOT_EPSG = 3035
POINT_LOCATIONS = ("center", "top-left", "top-right", "bottom-left", "bottom-right")

Bounds = dict[str, Any]


class SpatialBounds:
    """
    Handles spatial bounds from either a GeoSeries or a bounds dict.
    Provides both original (``xy``) and EPSG:4326 (``latlon``) dicts, plus
    margin-expanded variants.
    """

    def __init__(
        self,
        geometry: gpd.GeoSeries | None = None,
        bounds: Bounds | None = None,
        margin_km: float = 1.0,
        plot_name: str | None = None,
    ):
        self.margin_km = margin_km
        self.plot_name = plot_name
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

    @property
    def lat(self) -> float:
        """Latitude (EPSG:4326) of the plot centroid."""
        return self.centroid_latlon[0]

    @property
    def lon(self) -> float:
        """Longitude (EPSG:4326) of the plot centroid."""
        return self.centroid_latlon[1]

    @property
    def centroid_latlon(self) -> tuple:
        """``(lat, lon)`` of the plot centroid, computed in the original CRS then reprojected."""
        xy = self.xy
        cx, cy = (xy["west"] + xy["east"]) / 2, (xy["south"] + xy["north"]) / 2
        if xy["epsg"] == 4326:
            return cy, cx
        pt = gpd.GeoSeries(
            gpd.points_from_xy([cx], [cy]), crs=f"EPSG:{xy['epsg']}"
        ).to_crs(epsg=4326)
        return float(pt.y.iloc[0]), float(pt.x.iloc[0])

    @staticmethod
    def _to_latlon(bounds: Bounds, crs) -> Bounds:
        """Transform bounds to EPSG:4326 if needed."""
        if bounds["epsg"] == 4326:
            return copy.deepcopy(bounds)
        gdf = gpd.GeoSeries(
            [box(bounds["west"], bounds["south"], bounds["east"], bounds["north"])],
            crs=crs,
        )
        lon_min, lat_min, lon_max, lat_max = gdf.to_crs(epsg=4326).total_bounds
        return {
            "west": lon_min,
            "south": lat_min,
            "east": lon_max,
            "north": lat_max,
            "epsg": 4326,
        }

    @staticmethod
    def expand_bounds_km(bounds: Bounds, margin_km: float) -> Bounds:
        """Expand bounds by a fixed distance in kilometers on all sides."""
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

    @staticmethod
    def to_bbox(bounds: Bounds) -> list:
        """Return bounds as a ``[west, south, east, north]`` list."""
        return [bounds["west"], bounds["south"], bounds["east"], bounds["north"]]

    @property
    def expanded_xy(self) -> Bounds:
        """Original-CRS bounds expanded by ``margin_km``."""
        return self.expand_bounds_km(self.xy, self.margin_km)

    @property
    def expanded_latlon(self) -> Bounds:
        """
        Expanded bounds in EPSG:4326.
        Expands in the original CRS first, then reprojects (as done at initialization).
        """
        return self._to_latlon(self.expanded_xy, f"EPSG:{self.xy['epsg']}")

    def __repr__(self):
        return f"SpatialBounds(plot_name={self.plot_name!r}, original={self.xy}, latlon={self.latlon})"


def plot_square(
    point, point_location="center", size_m=PLOT_SIZE_M, epsg=PLOT_EPSG
) -> gpd.GeoSeries:
    """
    Square of ``size_m`` x ``size_m`` in ``epsg`` (default EPSG:3035) anchored at ``point``.

    ``point`` is a shapely Point (EPSG:4326) or a GeoSeries whose first geometry is used (EPSG:4326 if no CRS).
    ``point_location`` states which part of the square the point is:
    "center", "top-left", "top-right", "bottom-left" or "bottom-right".
    """
    if point_location not in POINT_LOCATIONS:
        raise ValueError(
            f"point_location must be one of {POINT_LOCATIONS}, got {point_location!r}"
        )
    series = (
        point
        if isinstance(point, gpd.GeoSeries)
        else gpd.GeoSeries([point], crs="EPSG:4326")
    )
    if series.crs is None:
        series = series.set_crs(epsg=4326)
    x, y = series.to_crs(epsg=epsg).iloc[0].coords[0][:2]

    vertical, _, horizontal = point_location.partition("-")
    if point_location == "center":
        west, south = x - size_m / 2, y - size_m / 2
    else:
        west = x if horizontal == "left" else x - size_m
        south = y - size_m if vertical == "top" else y
    return gpd.GeoSeries(
        [box(west, south, west + size_m, south + size_m)], crs=f"EPSG:{epsg}"
    )


def create_bbox_geoseries(lat, lon, location="center", size=100, epsg=3035):
    """
    Create a size x size (meters) bounding box in EPSG:epsg for a given (lat, lon) point.
    Returns a GeoSeries with the bbox polygon.
    """
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    x, y = transformer.transform(lon, lat)

    half = size / 2
    offsets = {
        "center": (-half, -half, half, half),
        "top-left": (0, -size, size, 0),
        "top-right": (-size, -size, 0, 0),
        "bottom-left": (0, 0, size, size),
        "bottom-right": (-size, 0, 0, size),
    }
    if location not in offsets:
        raise ValueError(f"Invalid location: {location}")

    dx_min, dy_min, dx_max, dy_max = offsets[location]
    minx = x + dx_min
    miny = y + dy_min
    maxx = x + dx_max
    maxy = y + dy_max

    return gpd.GeoSeries([box(minx, miny, maxx, maxy)], crs=f"EPSG:{epsg}")


def select_plot(df, plot_name, margin_km=1.0, point_location="bottom-left", size=100):
    """
    Select a plot by ``plot_name`` from an EFI GeoDataFrame.

    The table geometry is a point; it is used as the ``point_location`` anchor
    ("center", "top-left", "top-right", "bottom-left", "bottom-right") of a
    100 m x 100 m square in EPSG:3035, which defines the :class:`SpatialBounds`.

    Returns ``(plot_spatial, extents)`` where ``extents`` maps labels to bounds
    dicts (plot and surrounding window) for use in the statistics tables.
    """
    selected_plot = df.loc[df.plot_name == plot_name]
    if selected_plot.empty:
        raise ValueError(f"Plot '{plot_name}' not found in the EFI plot table")

    square = create_bbox_geoseries(
        selected_plot["lat"].values,
        selected_plot["lon"].values,
        location=point_location,
        size=size,
    )

    plot_spatial = SpatialBounds(square, margin_km=margin_km, plot_name=plot_name)
    extents = {
        "100m plot": plot_spatial.xy,
        f"{margin_km * 2:g} km window": plot_spatial.expanded_xy,
    }
    return plot_spatial, extents
