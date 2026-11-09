"""Pixel statistics and class distributions for loaded layers.

Table builders take ``extents``: a mapping ``{extent_label: bounds}`` where
``bounds`` is a dict with 'west', 'south', 'east', 'north', 'epsg' (e.g.
``{"100m plot": plot_spatial.xy, "2 km window": plot_spatial.expanded_xy}``),
so the same code works for any number of spatial extents.
"""

from typing import Dict, Mapping

import numpy as np
import pandas as pd

Bounds = Dict[str, object]


def class_distribution_percent(masked_data) -> pd.DataFrame:
    """
    Percentage distribution of classes over the valid pixels of a masked array.
    Returns a DataFrame with columns 'class' and 'percent', sorted by class.
    """
    valid = np.ma.asarray(masked_data).compressed()
    if valid.size == 0:
        return pd.DataFrame(columns=["class", "percent"])
    classes, counts = np.unique(valid, return_counts=True)
    df = pd.DataFrame({"class": classes.astype(int), "percent": counts / counts.sum() * 100.0})
    return df.sort_values("class").reset_index(drop=True)


def get_stats(data, layer_name, extent_name, cover_data=None, debug=False) -> pd.DataFrame:
    """
    Summary statistics of a continuous DataArray. If ``cover_data`` is given,
    pixels where it is masked or <= 0 are excluded. ``debug=True`` returns the
    full set of statistics instead of just the mean.
    """
    if cover_data is not None:
        tree_mask = np.ma.getmaskarray(cover_data) | (cover_data <= 0)
        data = np.ma.array(data, mask=np.ma.getmaskarray(data) | tree_mask)

    valid = data.to_masked_array().compressed()

    if valid.size == 0:
        stats = {"n_valid_pixels": 0, "min": np.nan, "p50": np.nan, "p95": np.nan,
                 "p99": np.nan, "max": np.nan, "mean": np.nan}
    else:
        p50, p95, p99 = np.percentile(valid, [50, 95, 99])
        stats = {"n_valid_pixels": valid.size, "min": valid.min(), "p50": p50, "p95": p95,
                 "p99": p99, "max": valid.max(), "mean": valid.mean()}

    row = {"layer_name": layer_name, "extent_name": extent_name}
    row.update(stats if debug else {"mean": stats["mean"]})
    return pd.DataFrame([row])


def compute_disturbance_stats(
    years, extents: Mapping[str, Bounds], disturbance_layer, agent_layer, agent_names
) -> pd.DataFrame:
    """
    Yearly disturbance summary for each extent in ``extents``.
    Only years with at least one disturbed pixel are returned; per-agent pixel
    counts are added as "<agent name> (pixels)" columns. The first column
    "Extent" holds the extent label.
    """
    summary_data = []
    for extent_name, bounds in extents.items():
        for year in years:
            disturbance = disturbance_layer.load_data(bounds, year=year).values
            agents = agent_layer.load_data(bounds, year=year).values

            disturbed = disturbance > 0
            disturbed_pixels = int(np.sum(disturbed))
            if disturbed_pixels == 0:
                continue
            total_pixels = int(disturbance.size)

            row = {
                "Extent": extent_name,
                "Year": year,
                "Total_Pixels": total_pixels,
                "Disturbed_Pixels": disturbed_pixels,
                "Disturbed_%": disturbed_pixels / total_pixels * 100 if total_pixels else 0.0,
            }
            for agent in np.unique(agents[disturbed]):
                if not np.isnan(agent): 
                    agent_id = int(agent)
                    label = f"{agent_names.get(agent_id, f'Agent_{agent_id}')} (pixels)"
                    row[label] = int(np.sum((agents == agent) & disturbed))
            summary_data.append(row)
    table = pd.DataFrame(summary_data).fillna(0)
    pixel_cols = [c for c in table.columns if c.endswith("(pixels)")]
    table[pixel_cols] = table[pixel_cols].astype(int)
    return table


def class_distribution_table(layer, extents: Mapping[str, Bounds], **load_kwargs) -> pd.DataFrame:
    """
    Class distribution (%) of a classified layer for several extents.

    Returns columns ``class``, ``class_name`` and one column per extent label
    (percentage of valid pixels; 0 where a class is absent). The number of
    valid pixels per extent is stored in ``table.attrs['n_pixels']``.
    """
    table = None
    n_pixels = {}
    for extent_name, bounds in extents.items():
        data = layer.load_data(bounds, True, **load_kwargs)
        n_pixels[extent_name] = int(np.ma.asarray(data).count())
        dist = class_distribution_percent(data)
        dist = dist.rename(columns={"percent": extent_name})
        table = dist if table is None else pd.merge(table, dist, on="class", how="outer")
    if table is None:
        return pd.DataFrame(columns=["class", "class_name"])
    table = table.fillna(0)
    class_dict = layer.class_dict or {}
    table.insert(1, "class_name", table["class"].map(lambda c: class_dict.get(c, f"Unknown ({c})")))
    table = table.sort_values("class").reset_index(drop=True)
    table.attrs["n_pixels"] = n_pixels
    return table


def layer_stats_table(layers: Mapping[str, object], extents: Mapping[str, Bounds], debug=False) -> pd.DataFrame:
    """
    Summary statistics of continuous layers for several extents.

    ``layers`` maps a label to a layer (``ClassMap``). One row per
    (layer, extent), built with :func:`get_stats`.
    """
    rows = [
        get_stats(layer.load_data(bounds), layer_name, extent_name, debug=debug)
        for layer_name, layer in layers.items()
        for extent_name, bounds in extents.items()
    ]
    return pd.concat(rows, axis=0).reset_index(drop=True) if rows else pd.DataFrame()
