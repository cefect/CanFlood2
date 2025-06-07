.. _sec02-userGuide:


User Guide
==========================


Vertical Basis
--------------------------
For the core damage function operations within CanFlood, ensuring the vertical basis is consistent between parameters and data is essential for accurate calculations.
In simple cases, the **asset inventory** provides asset height values (relative to ground) while the remaining datasets provide elevation information.
However, CanFlood supports more complex combinations of vertical basis from the following datasets:
    - **Asset Inventory**: Provides asset elevation values in the `elevation` field (for each function group). When the **elevation type** parameter is set to `relative`, the values are interepted as relative to the DEM (:math:`FH`) (i.e., height above ground). When set to `absolute`, the values are interpreted as absolute elevations (i.e., relative to the project vertical datum) (:math:`FE`).

    - **Hazard Event Grids**: Provides flood hazard values as a raster grid. Currently, only **Water Surface Levels** (:math:`WSL`) are supported, which represent absolute flood surface elevations. Support for **Water Surface Heights** (:math:`WSH`), which represent flood depth above ground, may be added in future versions.
 
    - **DEM**: Provides ground elevation values (:math:`DEM`) as a raster grid. These are always treated as absolute elevations and are required only when the asset inventory provides relative height values (i.e., when *Elevation type* is set to `relative`).


The supported combinations of these vertical bases, and the corresponding depth calculation formulas, are summarized in :numref:`tab-depth-formulas`, where :math:`i` represents an individual asset and :math:`D` is the depth used in the damage function calculation.

.. table:: Supported combinations of flood hazard layers and inventory elevation types
   :name: tab-depth-formulas
   :align: center

   +-----------+------------+-----+-----------+---------------------------------------------------------------+
   | Hazard    | Inventory  | DEM | Supported | Depth-calculation formula                                     |
   +===========+============+=====+===========+===============================================================+
   | WSL       | height     | yes | yes       | :math:`D_{i} = WSL_{i} - \left(DEM_{i} + FH_{i}\right)`       |
   +-----------+------------+-----+-----------+---------------------------------------------------------------+
   | WSL       | elevation  | no  | yes       | :math:`D_{i} = WSL_{i} - FE_{i}`                              |
   +-----------+------------+-----+-----------+---------------------------------------------------------------+
   | WSH       | height     | no  | no        | :math:`D_{i} = WSH_{i} - FH_{i}`                              |
   +-----------+------------+-----+-----------+---------------------------------------------------------------+
   | WSH       | elevation  | yes | no        | :math:`D_{i} = WSH_{i} - \left(FE_{i} - DEM_{i}\right)`       |
   +-----------+------------+-----+-----------+---------------------------------------------------------------+



