"""Matplotlib plotting helpers for map layers."""

import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from IPython.display import HTML, display
from matplotlib import pyplot as plt


def overlay_rectangle(ax, extent, edgecolor="black", facecolor="none", linewidth=1, label=None, zorder=4):
    """
    Overlay a rectangle on the axes for the given extent.
    extent: dict with keys 'west', 'south', 'east', 'north'
    """
    rect = mpatches.Rectangle(
        (extent["west"], extent["south"]),
        extent["east"] - extent["west"],
        extent["north"] - extent["south"],
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
            bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=2),
        )


def plot_map(data, layer, ax=None, overlay_extent=None, overlay_label=None, title=None, **kwargs):
    """
    Plot a DataArray (with 2D ``lon``/``lat`` coords) styled by a layer.

    layer must expose ``cmap``, ``norm``, ``legend_handles`` and ``name``
    (see :class:`utils.layers.ClassMap`). Classified layers get a patch legend,
    continuous layers a colorbar. ``kwargs`` (e.g. vmin/vmax) are passed to
    ``pcolormesh`` for continuous layers only.
    """
    if ax is None:
        # continuous layers lose ~9% of the axes width to the colorbar; widen the
        # figure so the map panel keeps the same size as for classified layers
        width = 6 if layer.legend_handles is not None else 6.6
        fig, ax = plt.subplots(figsize=(width, 5), dpi=150)
    else:
        fig = ax.get_figure()

    if layer.norm is not None:
        im = ax.pcolormesh(data.lon, data.lat, data.values, cmap=layer.cmap, norm=layer.norm)
    else:
        im = ax.pcolormesh(data.lon, data.lat, data.values, cmap=layer.cmap, **kwargs)
    ax.set_title(title if title is not None else layer.name)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    if layer.legend_handles is not None:
        ax.legend(handles=layer.legend_handles, loc="upper left",
                  bbox_to_anchor=(1.01, 1), fontsize=8, framealpha=0.9)
    else:
        cbar = fig.colorbar(im, ax=ax, orientation="vertical", fraction=0.046, pad=0.04)
        cbar.set_label(data.attrs.get("units") or layer.units, rotation=270, labelpad=15)

    if overlay_extent:
        overlay_rectangle(ax, overlay_extent, label=overlay_label)
    return fig


def style_table(df, columns=None, cmap="YlGn", vmin=None, vmax=None, precision=1):
    """
    Return a pandas Styler with a background gradient on ``columns``.

    By default all numeric columns are colored, except identifier-like columns
    ('class', 'Year'). Use ``vmin``/``vmax`` (e.g. 0/100 for percentages) for a
    fixed color scale shared by all columns.
    """
    if columns is None:
        skip = {"class", "Year"}
        columns = [c for c in df.select_dtypes("number").columns if c not in skip]
    styler = df.style.hide(axis="index").format(precision=precision)
    if columns:
        styler = styler.background_gradient(subset=columns, cmap=cmap, vmin=vmin, vmax=vmax)
    return styler


def show_bbox_table(dict1, dict2, plot_name, col_names=None):
    """Display a table comparing two bounds dicts (e.g. projected and EPSG:4326)."""
    if col_names is None:
        col_names = [f"{dict1['epsg']}", "4326"]
    keys = ["west", "south", "east", "north"]
    df = pd.DataFrame(
        {col_names[0]: [dict1[k] for k in keys], col_names[1]: [dict2[k] for k in keys]},
        index=[k.capitalize() for k in keys],
    )
    display(HTML(f"<h3>{plot_name}</h3>"))
    display(df)


def plot_class_distribution(df, title=None, ax=None, color_dict=None):
    """
    Grouped horizontal bar chart of a table from ``class_distribution_table``.

    One group per class (classes absent from every extent are dropped) and one
    bar per extent column. The legend shows the number of valid pixels per
    extent when ``df.attrs['n_pixels']`` is set. The x axis is shared in percent, starting at 0.
    """
    extent_cols = [c for c in df.columns if c not in ("class", "class_name")]
    data = df.loc[(df[extent_cols] > 0).any(axis=1)]
    if ax is None:
        _, ax = plt.subplots(figsize=(8, max(3, 0.6 * len(data) + 1.5)), dpi=150)
    fig = ax.get_figure()

    n_pixels = df.attrs.get("n_pixels", {})
    height = 0.8 / max(len(extent_cols), 1)
    positions = np.arange(len(data))
    colors = color_dict or dict(zip(extent_cols, plt.get_cmap("Set2").colors))
    for i, col in enumerate(extent_cols):
        offset = (i - (len(extent_cols) - 1) / 2) * height
        n = n_pixels.get(col)
        label = col if n is None else f"{col} (n = {n:,} px)"
        bars = ax.barh(positions + offset, data[col], height=height, label=label, color=colors.get(col))
        ax.bar_label(bars, labels=[f"{v:.1f}" if v > 0 else "" for v in data[col]], fontsize=7, padding=2)

    ax.invert_yaxis()
    ax.set_yticks(positions)
    ax.set_yticklabels(data["class_name"])
    ax.set_xlim(0, min(100, data[extent_cols].to_numpy().max() * 1.15) if len(data) else 100)
    ax.set_xlabel("Share of valid pixels (%)")
    ax.set_title(title or "Class distribution")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(title="Extent", loc="best", fontsize=8)
    fig.tight_layout()
    return fig


def plot_disturbance_timeline(df, years, agent_names, agent_colors, title=None):
    """
    Yearly disturbed share (%) for every extent, stacked by disturbance agent.

    ``df`` comes from ``compute_disturbance_stats`` (only disturbed years);
    years without disturbance are drawn as zero so the x axis always spans
    ``years``. Each extent has its own y axis because plot and window shares
    differ by orders of magnitude. Disturbed pixels without a known agent are
    shown as "Unknown agent".
    """
    years = list(years)
    extents = list(df["Extent"].unique()) if len(df) else []
    fig, axes = plt.subplots(
        max(len(extents), 1), 1, figsize=(12, 3 * max(len(extents), 1)),
        dpi=150, sharex=True, squeeze=False,
    )
    agent_cols = {f"{name} (pixels)": (name, agent_colors.get(k)) for k, name in agent_names.items()}

    for ax, extent in zip(axes[:, 0], extents):
        sub = df[df["Extent"] == extent].set_index("Year").reindex(years)
        total = sub["Total_Pixels"].ffill().bfill()
        known = 0
        bottom = np.zeros(len(years))
        for col, (name, color) in agent_cols.items():
            if col not in sub:
                continue
            counts = sub[col].fillna(0).to_numpy()
            known = known + counts
            share = counts / total.to_numpy() * 100
            ax.bar(years, share, bottom=bottom, color=color, label=name, width=0.8)
            bottom += share
        unknown = (sub["Disturbed_Pixels"].fillna(0).to_numpy() - known).clip(min=0)
        ax.bar(years, unknown / total.to_numpy() * 100, bottom=bottom,
               color="lightgrey", label="Unknown agent", width=0.8)
        ax.set_title(extent, fontsize=10, loc="left")
        ax.set_ylabel("Disturbed (%)")
        ax.set_ylim(0, max(sub["Disturbed_%"].max(skipna=True) * 1.1, 1e-3) if sub["Disturbed_%"].notna().any() else 1)
        ax.grid(axis="y", alpha=0.3)

    axes[-1, 0].set_xlim(years[0] - 0.5, years[-1] + 0.5)
    axes[-1, 0].set_xticks([y for y in years if y % 5 == 0])
    axes[-1, 0].set_xlabel("Year")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper right", fontsize=8, ncol=len(labels))
    fig.suptitle(title or "Forest disturbance per year", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


def map_plot_location(df, plot_name, zoom_start=5, show_other_plots=True):
    """
    Interactive folium map at European scale showing where ``plot_name`` is.

    The selected plot gets a red marker with its name (and its outline, visible
    when zooming in); other EFI plots are small grey dots. Returns a
    ``folium.Map`` (display it as the last expression of a notebook cell).
    """
    import folium  # lazy: only needed for interactive maps

    selected = df.loc[df.plot_name == plot_name]
    if selected.empty:
        raise ValueError(f"Plot '{plot_name}' not found in the EFI plot table")
    center = selected.geometry.centroid.to_crs(4326).iloc[0]

    fmap = folium.Map(location=[center.y, center.x], zoom_start=zoom_start, tiles="OpenStreetMap")
    if show_other_plots:
        others = df.loc[df.plot_name != plot_name]
        for name, pt in zip(others.plot_name, others.geometry.centroid.to_crs(4326)):
            folium.CircleMarker([pt.y, pt.x], radius=3, color="grey", fill=True,
                                weight=1, tooltip=str(name)).add_to(fmap)
    folium.GeoJson(
        selected.to_crs(4326)[["plot_name", "geometry"]].to_json(),
        style_function=lambda _: {"color": "red", "fillColor": "red", "weight": 2},
    ).add_to(fmap)
    folium.Marker([center.y, center.x], tooltip=plot_name,
                  icon=folium.Icon(color="red", icon="tree", prefix="fa")).add_to(fmap)
    return fmap


def map_all_plots(df, zoom_start=4):
    """
    Interactive folium map of all EFI plots.

    Hover a marker to see the plot name.
    The view is fitted and locked to the bounding box of all plots (plus a 1° margin).
    Intended for notebook exploration (not for slide export; use
    :func:`map_plot_location` for that). Returns a ``folium.Map``.
    """
    import folium  # lazy: only needed for interactive maps

    pts = df.geometry.centroid.to_crs(4326)
    pad = 1.0  # degrees of margin around the plots
    west, south, east, north = pts.x.min() - pad, pts.y.min() - pad, pts.x.max() + pad, pts.y.max() + pad
    fmap = folium.Map(location=[pts.y.mean(), pts.x.mean()], zoom_start=zoom_start,
                      tiles="OpenStreetMap", max_bounds=True,
                      min_lon=west, max_lon=east, min_lat=south, max_lat=north,
                      max_bounds_viscosity=1.0)
    for name, pt in zip(df.plot_name, pts):
        folium.CircleMarker([pt.y, pt.x], radius=5, color="black", weight=1, fill=True,
                            fill_color="red", fill_opacity=0.9, tooltip=str(name)).add_to(fmap)
    fmap.fit_bounds([[south, west], [north, east]])
    return fmap


def pick_plot_on_map(df, default=None, width=900, height=500):
    """
    Choose an EFI plot by clicking its marker on a map or via a drop-down.

    Displays an interactive ipyleaflet map (``width`` x ``height`` px, zoomed to
    the bounding box of all plots; hover a marker for the plot name, click to
    select it; the selection is highlighted in red) above a drop-down that
    stays in sync. Returns the ``ipywidgets.Dropdown``; read the chosen
    plot from its ``.value`` in a later cell. Needs a live kernel (ipyleaflet
    sends the click back to Python), so it does not work in exported HTML/slides.
    """
    import ipywidgets as widgets
    from ipyleaflet import CircleMarker, Map, Marker, basemaps

    names = list(df.plot_name)
    pts = df.geometry.centroid.to_crs(4326)
    coords = {n: (pt.y, pt.x) for n, pt in zip(names, pts)}
    dropdown = widgets.Dropdown(options=sorted(names), value=default if default in coords else sorted(names)[0],
                                description="Plot:", layout=widgets.Layout(width="400px"))

    # fit_bounds is unreliable before the widget has a rendered size, so the
    # zoom for a fixed pixel size is computed here (Web Mercator, 256 px tiles).
    def mercator_y(lat):
        return np.log(np.tan(np.pi / 4 + np.deg2rad(lat) / 2))

    lon_span = max(pts.x.max() - pts.x.min(), 1e-3) * 1.15
    y_span = max(mercator_y(pts.y.max()) - mercator_y(pts.y.min()), 1e-5) * 1.15
    zoom = int(np.floor(min(np.log2(width * 360 / (256 * lon_span)),
                            np.log2(height * 2 * np.pi / (256 * y_span)))))
    zoom = int(np.clip(zoom, 1, 15))
    fmap = Map(center=((pts.y.max() + pts.y.min()) / 2, (pts.x.max() + pts.x.min()) / 2),
               zoom=zoom, basemap=basemaps.OpenStreetMap.Mapnik,
               layout=widgets.Layout(width=f"{width}px", height=f"{height}px"))
    highlight = CircleMarker(location=coords[dropdown.value], radius=12, color="red",
                             fill_color="red", fill_opacity=0.4)
    fmap.add(highlight)

    def make_click_handler(name):
        def handler(**_):
            dropdown.value = name
        return handler

    for name, loc in coords.items():
        marker = Marker(location=loc, title=str(name), draggable=False)
        marker.on_click(make_click_handler(name))
        fmap.add(marker)

    def on_change(change):
        highlight.location = coords[change["new"]]

    dropdown.observe(on_change, names="value")
    display(widgets.VBox([dropdown, fmap]))
    return dropdown


def plot_value_distributions(layers, extents, bins=40, title=None):
    """
    Histograms of continuous layers (e.g. canopy height, FHD) per extent.

    Integer-valued layers get one bin per value (wider integer steps if the
    range exceeds 100 values) so the histogram has no empty gaps.

    ``layers`` maps a label to a layer (``ClassMap``) and ``extents`` maps a
    label to bounds, as in :func:`utils.stats.layer_stats_table`. One panel per
    layer; each extent is a density histogram (so a 100 m plot and a km-scale
    window are comparable) with a dashed line at its mean. The legend shows the
    number of valid pixels and the mean. The x label shows the layer's unit
    (``layer.units`` or the raster's ``units`` tag).
    """
    fig, axes = plt.subplots(1, len(layers), figsize=(6 * len(layers), 4), dpi=150, squeeze=False)
    colors = plt.get_cmap("Set2").colors

    for ax, (label, layer) in zip(axes[0], layers.items()):
        values, units = {}, ""
        for extent, bounds in extents.items():
            da = layer.load_data(bounds)
            units = da.attrs.get("units", "") or layer.units or units
            values[extent] = np.ma.asarray(da.to_masked_array()).compressed()

        pooled = np.concatenate([v for v in values.values() if v.size] or [np.array([0.0, 1.0])])
        if np.allclose(pooled, np.round(pooled)) and pooled.max() - pooled.min() >= 1:
            # integer-valued layer (e.g. canopy height in m): one bin per value,
            # otherwise some bins hold no integer and show up as gaps
            step = max(1, int(np.ceil((pooled.max() - pooled.min() + 1) / 100)))
            edges = np.arange(pooled.min() - 0.5, pooled.max() + 0.5 + step, step)
        else:
            edges = np.linspace(pooled.min(), pooled.max(), bins + 1)
        for i, (extent, v) in enumerate(values.items()):
            color = colors[i % len(colors)]
            if v.size == 0:
                ax.plot([], [], color=color, label=f"{extent} (no valid pixels)")
                continue
            ax.hist(v, bins=edges, density=True, histtype="stepfilled", alpha=0.3, color=color)
            ax.hist(v, bins=edges, density=True, histtype="step", color=color, linewidth=1.5,
                    label=f"{extent} (n = {v.size:,} px, mean = {v.mean():.2f})")
            ax.axvline(v.mean(), color=color, linestyle="--", linewidth=1)
        ax.set_xlabel(f"{layer.name} ({units})" if units else layer.name)
        ax.set_ylabel("Density")
        ax.set_title(label)
        ax.grid(alpha=0.3)
        ax.legend(title="Extent", loc="best", fontsize=7)

    if title:
        fig.suptitle(title)
    fig.tight_layout()
    return fig
