"""
Layer configurations for the WorldForest EFI tool.

Each ``*_MAP``-style dict is passed as keyword arguments to
:class:`utils.layers.ClassMap`. Keys:

- ``name``: display name used as plot title
- ``filename``: local raster/VRT path (may contain ``{year}`` for yearly layers)
- ``collection``: STAC collection id (alternative to ``filename``)
- ``class_dict`` / ``class_colors``: class id -> label / color for classified layers
- ``cmap``: matplotlib colormap name for continuous layers
"""

DISTURBANCE_YEARS = range(1985, 2025)

GENUS_MAP = {
    "name": "Genus map",
    "filename": "/data/open/worldforest/TreeGenusMap/spp_pred.vrt",
    "class_dict": {
        0: "Larix",
        1: "Picea",
        2: "Pinus",
        3: "Fagus",
        4: "Quercus",
        5: "Other needleleaf",
        6: "Other broadleaf",
        7: "No tree",
    },
    "class_colors": {
        0: (7, 116, 224),    # Larix
        1: (232, 235, 63),   # Picea
        2: (230, 62, 236),   # Pinus
        3: (139, 240, 76),   # Fagus
        4: (51, 146, 11),    # Quercus
        5: (176, 66, 226),   # Other needleleaf
        6: (221, 157, 173),  # Other broadleaf
        7: (255, 255, 255),  # No tree
    },
}

CANOPY_HEIGHT = {
    "name": "Canopy height",
    "filename": "/data/open/worldforest/CanopyHeight/merged_pred_q050.vrt",
    "cmap": "viridis",
    "units": "m",
}

FOLIAGE_HEIGHT_DIVERSITY = {
    "name": "Foliage Height Diversity",
    "filename": "/data/open/worldforest/FoliageHeightDiversity/map.vrt",
    "cmap": "plasma",
    "units": "dimensionless index",
}

LANDCOVER = {
    "name": "LCFM landcover map",
    "collection": "lcfm-lcm-10",
    "class_dict": {
        10: "Tree cover",
        20: "Shrubland",
        30: "Grassland",
        40: "Cropland",
        50: "Herbaceous wetland",
        60: "Mangroves",
        70: "Moss and lichen",
        80: "Bare/sparse vegetation",
        90: "Built up",
        100: "Permanent water bodies",
        110: "Snow and ice",
    },
    "class_colors": {
        10: "#006400",
        20: "#ffbb22",
        30: "#ffff4c",
        40: "#f096ff",
        50: "#0096a0",
        60: "#00cf75",
        70: "#fae6a0",
        80: "#b4b4b4",
        90: "#fa0000",
        100: "#0064c8",
        110: "#f0f0f0",
    },
}

# Forest Disturbance Atlas
AGENT_CLASS_NAMES = {
    1: "Wind/bark beetle complex",
    2: "Fire",
    3: "Harvest",
    4: "Mixed agent",
}
AGENT_CLASS_COLORS = {
    1: "#377eb8",
    2: "#e41a1c",
    3: "#4daf4a",
    4: "#984ea3",
}

ANNUAL_DISTURBANCE = {
    "name": "Annual Disturbance",
    "filename": "/data/open/worldforest/ForestDisturbanceAtlas/AnnualDisturbance/annual_disturbance_{year}.vrt",
}

DISTURBANCE_AGENT = {
    "name": "Disturbance Agent",
    "filename": "/data/open/worldforest/ForestDisturbanceAtlas/DisturbanceAgent/disturbance_agent_{year}.vrt",
}

LATEST_DISTURBANCE = {
    "name": "Latest Disturbance",
    "filename": "/data/open/worldforest/ForestDisturbanceAtlas/LatestDisturbance/latest_disturbance.vrt",
    "cmap": "Spectral_r",
    "units": "year",
}

AGENT_AGGREGATED = {
    "name": "Disturbance Agent Aggregated",
    "filename": "/data/open/worldforest/ForestDisturbanceAtlas/DisturbanceAgentAggregated/disturbance_agent_aggregated.vrt",
    "class_dict": AGENT_CLASS_NAMES,
    "class_colors": AGENT_CLASS_COLORS,
}

COMBINED_DROUGHT_INDICATOR = {
    "name": "Combined Drought Indicator",
    "datafolder": "/data/open/worldforest/CombinedDroughtIndicator/",
    "class_dict": {
        0: "No drought",
        1: "Watch. Precipitation deficit",
        2: "Warning. Soil moisture deficit following precipitation deficit",
        3: "Alert. Vegetation stress following precipitation / soil moisture deficit",
        4: "Recovery to normal condition",
        5: "Temporary soil moisture recovery",
        6: "Temporary vegetation recovery",
        7: "No data inside LISFLOOD domain",
        8: "Outside LISFLOOD domain",
    },
    "class_colors": {
        0: "#d9d9d9",  # 0: No drought (grey)
        1: "#a6bddb",  # 1: Watch (light blue)
        2: "#3690c0",  # 2: Warning (blue)
        3: "#f03b20",  # 3: Alert (red)
        4: "#31a354",  # 4: Recovery (green)
        5: "#feb24c",  # 5: Temp soil moisture recovery (orange)
        6: "#ffeda0",  # 6: Temp vegetation recovery (yellow)
        7: "#636363",  # 7: No data inside LISFLOOD (dark grey)
        8: "#000000",  # 8: Outside LISFLOOD (black)
    }
}
