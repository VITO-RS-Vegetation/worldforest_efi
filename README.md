# worldforest_efi

Loads WorldForest / LCFM map layers for EFI plots and computes statistics and figures.
The workflow lives in `WF_tool_prototype.ipynb` and is run on a remote desktop with access to the data.

## Code layout (`utils/`)

| Module | Purpose |
|---|---|
| `parameters.py` | Layer configurations: raster paths, STAC collections, class names/colors |
| `spatial.py` | `SpatialBounds` – plot extents in the original CRS and EPSG:4326, with km margins |
| `layers.py` | `ClassMap` – a map layer loaded from a local raster or a STAC collection, with colormap/legend |
| `plotting.py` | `plot_map` / `overlay_rectangle` matplotlib helpers, `style_table` for colored DataFrames |
| `stats.py` | Multi-extent tables: `class_distribution_table`, `layer_stats_table`, `compute_disturbance_stats` (+ `get_stats`, `class_distribution_percent`) |
| `read_stac.py` | STAC search (`stac.terrascope.be`) and reading of local assets |
| `worldforest.py` | Facade: re-exports the above and instantiates the configured layers |

```python
from utils import worldforest as wf

plot_spatial = wf.SpatialBounds(selected_plot.geometry, margin_km=1.0)
data = wf.land_cover.load_data(plot_spatial.expanded_xy)   # STAC collection "lcfm-lcm-10"
wf.land_cover.plot(data, overlay_extent=plot_spatial.latlon)
```
