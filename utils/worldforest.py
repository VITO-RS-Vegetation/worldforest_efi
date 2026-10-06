"""
Public facade for the WorldForest EFI tool.

Re-exports the building blocks (SpatialBounds, ClassMap, plotting and stats
helpers) and instantiates the configured layers from :mod:`utils.parameters`.

Typical use::

    from utils import worldforest as wf
    plot_spatial = wf.SpatialBounds(selected_plot.geometry, margin_km=1.0)
    data = wf.genus_map_class.load_data(plot_spatial.expanded_xy)
    wf.genus_map_class.plot(data, overlay_extent=plot_spatial.latlon)
"""

from . import parameters
from .layers import ClassMap
from .plotting import overlay_rectangle, plot_map
from .spatial import SpatialBounds
from .plotting import style_table
from .stats import class_distribution_percent, class_distribution_table, get_stats, layer_stats_table
from .stats import compute_disturbance_stats as _compute_disturbance_stats

# Configured layers -----------------------------------------------------------
genus_map_class = ClassMap(**parameters.GENUS_MAP)
canopy_height_class = ClassMap(**parameters.CANOPY_HEIGHT)
foliage_height_diversity_class = ClassMap(**parameters.FOLIAGE_HEIGHT_DIVERSITY)
land_cover = ClassMap(**parameters.LANDCOVER)

years = parameters.DISTURBANCE_YEARS
annual_disturbance_class = ClassMap(**parameters.ANNUAL_DISTURBANCE, years=years)
disturbance_agent_class = ClassMap(**parameters.DISTURBANCE_AGENT, years=years)
latest_disturbance_class = ClassMap(**parameters.LATEST_DISTURBANCE)
agent_aggregated_class = ClassMap(**parameters.AGENT_AGGREGATED)


def compute_disturbance_stats(years, extents):
    """
    Yearly disturbance summary using the configured Forest Disturbance Atlas layers.
    ``extents`` maps extent labels to bounds dicts (see :mod:`utils.stats`).
    """
    return _compute_disturbance_stats(
        years,
        extents,
        disturbance_layer=annual_disturbance_class,
        agent_layer=disturbance_agent_class,
        agent_names=parameters.AGENT_CLASS_NAMES,
    )


__all__ = [
    "parameters",
    "ClassMap",
    "SpatialBounds",
    "plot_map",
    "overlay_rectangle",
    "style_table",
    "class_distribution_percent",
    "class_distribution_table",
    "get_stats",
    "layer_stats_table",
    "compute_disturbance_stats",
    "genus_map_class",
    "canopy_height_class",
    "foliage_height_diversity_class",
    "land_cover",
    "annual_disturbance_class",
    "disturbance_agent_class",
    "latest_disturbance_class",
    "agent_aggregated_class",
]
