"""
WorldForest EFI utilities.

Modules:
- ``parameters``: layer configurations (paths, STAC collections, class tables)
- ``spatial``: :class:`SpatialBounds` for plot extents and ``select_plot``
- ``layers``: :class:`ClassMap` and :class:`DatedClassMap` layer loading (raster / STAC) and class styling
- ``plotting``: matplotlib figures, folium/ipyleaflet plot-selection maps
- ``stats``: pixel statistics and class distributions
- ``read_stac``: STAC search and local-asset reading
- ``worldforest``: facade with configured layer instances
"""
