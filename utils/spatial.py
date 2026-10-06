"""Spatial extent handling for EFI plots (original CRS and EPSG:4326 bounds)."""

import copy
import math
from typing import Any, Dict, Optional

import geopandas as gpd
from shapely.geometry import box

Bounds = Dict[str, Any]


class SpatialBounds:
    """
    Handles spatial bounds from either a GeoSeries or a bounds dict.
    Provides both original (``xy``) and EPSG:4326 (``latlon``) dicts, plus
    margin-expanded variants.
    """

    def __init__(
        self,
        geometry: Optional[gpd.GeoSeries] = None,
        bounds: Optional[Bounds] = None,
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
        return f"SpatialBounds(original={self.xy}, latlon={self.latlon})"
