# worldforest_efi

Shows WorldForest / LCFM map layers around a single **EFI 100 m × 100 m plot** and summarises them as
figures and tables. Every statistic is computed for several **spatial extents** (the plot itself and a
surrounding window) so the plot can be compared with its neighbourhood.
The workflow lives in `WF_tool_prototype.ipynb` and is run on a remote desktop with access to the data
(`/data/open/worldforest/...` rasters and the Terrascope STAC, `stac.terrascope.be`).

## Layers

All layers are available from `from utils import worldforest` and share the same interface
(`.load_data(extent)` and `.plot(data, ...)`).

|Layer                                       |Description                                                                              |
|--------------------------------------------|-----------------------------------------------------------------------------------------|
|`worldforest.genus_map_class`               |Dominant tree genus (classified)                                                         |
|`worldforest.canopy_height_class`           |Canopy height in m (continuous)                                                          |
|`worldforest.foliage_height_diversity_class`|Foliage height diversity, FHD (continuous)                                               |
|`worldforest.land_cover`                    |LCFM 10 m land cover, 11 thematic classes (classified, STAC collection `lcfm-lcm-10`)    |
|`worldforest.annual_disturbance_class`      |Forest Disturbance Atlas: disturbance per year, 1985–2024                                |
|`worldforest.disturbance_agent_class`       |Forest Disturbance Atlas: cause of disturbance per year, 1985–2024                       |
|`worldforest.latest_disturbance_class`      |Forest Disturbance Atlas: year of the most recent disturbance per pixel (continuous)     |
|`worldforest.agent_aggregated_class`        |Forest Disturbance Atlas: dominant disturbance agent per pixel (e.g. harvest, wind/bark beetle, fire)|

## Usage

See `WF_tool_prototype.ipynb` for the full workflow: plot selection, maps, statistics and figures for every layer.
