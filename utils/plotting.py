"""Matplotlib plotting helpers for map layers."""

import matplotlib.patches as mpatches
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
        fig, ax = plt.subplots(figsize=(6, 5), dpi=150)
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
        cbar.set_label(data.attrs.get("units"), rotation=270, labelpad=15)

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
