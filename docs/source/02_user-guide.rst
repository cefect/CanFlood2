.. _sec02-userGuide:


User Guide
==========================

.. _sec02-dataRequirements:

Data Requirements
--------------------------
CanFlood requires the following data for all models:
 

- **Asset Inventory**: One or more vector layers describing each of the asset types in your risk model suite. 
- **Hazard Event Water Grids**: A set of raster files representing the exposure for each hazard event (typically maximum flood water surface elevation).
- **Hazard Event Probabilities**: The probability associated with each hazard event.

More advanced CanFlood models may also require the following data:

- **DEM**: A raster of ground elevations for your study area (required for models using relative heights).
- **Study Area**: A polygon layer defining the study area, used for clipping asset data (*not yet implemented*).
- **Vulnerability Functions**: For depth-dependent models, a set of CanFlood-format vulnerability functions matching the `tag` values in your asset inventory.


.. _sec02-projDB:

Project Database
--------------------------

The project database is a SQLite database file that stores all the parameters and (non-spatial) data associated with a CanFlood project. 
Using the **Save** button on the main dialog will save the current project parameters and data to the database, while the **Save** button on the Model Configuration dialog will save the model specific parameters and data.
Similarly, **Run** functions will use the data stored in the database to compute new results tables which are also stored in the database.
Functions on the **Reporting** tab will read these tables and generate reports and plots (no changes to the database are made).
The following summarizes the tables in a complete project database:

.. table:: Project database tables
    :name: tab-project-db-tables
    :align: center

    +-------------------------------+----------------------------------------------------------------------------------------------+
    | Table Name                    | Description                                                                                  |
    +===============================+==============================================================================================+
    | 01_project_meta               | Stores project metadata                                                                      |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | 02_project_parameters         | Stores project parameters entered by the user                                                |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | 03_model_suite_index          | An index of all the models included in the project                                           |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | 04_haz_meta                   | Parameters specific to the hazard data                                                       |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | 05_haz_events                 | Hazard event probability and metadata                                                        |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | 06_vfunc_index                | Index of all the vulnerability functions loaded to the project                               |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | 07_vfunc_data                 | Data of all vulnerability functions                                                          |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | model_*_table_ead             | Results table of per-asset EAD values                                                        |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | model_*_table_expos           | Per-asset values sampled from hazard rasters                                                 |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | model_*_table_finv            | Asset inventory tabular data                                                                 |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | model_*_table_gels            | Per-asset values sampled from the DEM                                                        |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | model_*_table_impacts         | Results table of per-asset impact values (damage function results) and intermediate values   |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | model_*_table_impacts_prob    | Like model_*_table_impacts, but without intermediate values                                  |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | model_*_table_impacts_sum     | Results table of the sum of impacts per event. Used to plot the risk curve.                  |
    +-------------------------------+----------------------------------------------------------------------------------------------+
    | model_*_table_parameters      | Parameters for this model                                                                    |
    +-------------------------------+----------------------------------------------------------------------------------------------+


Model Configuration
--------------------------
The CanFlood2 model configuration dialog allows users to set parameters and data for each model in the suite.

Vertical basis
^^^^^^^^^^^^^^^^^^^^^^^^
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



Exposure Mode
^^^^^^^^^^^^^^^^^^^^^^^^

Through the exposure mode parameter, CanFlood supports two calculation routines for determining the `table_impacts`:

    - **binary (L1)**: This mode calculates the impacts based on whether the asset is exposed to flooding (1) or not (0). 
    - **depth-dependent (L2)**: This mode employs the vulnerability functions to calculate the impacts based on the depth of flooding.



Asset Inventory
^^^^^^^^^^^^^^^^^^^^^^^^
The :ref:`asset inventory <sec02-dataRequirements>` is a vector dataset that contains information about each asset to be included in the model.
This dataset is specified and further configured on the **Asset Inventory** tab of the Model Configuration dialog.
CanFlood extracts four data and one index field from this dataset:

- **Index FieldName**: The field that uniquely identifies each asset in the inventory.
- **elevation**: The field containing the elevation or height values.
- **scale**: The field containing the value by which the damage function result should be scaled (e.g., floor area).
- **cap**: The field containing the maximum impact value to allow for the asset (e.g., total replacement cost).
- **tag**: The field specifying the vulnerability function to use for each asset. This field must match the `tag` field in the.

All models require an **elevation** field be specified, while only the depth-dependent models require a **tag** field.
Other fields are optional. 

Asset Inventory: Function Groups
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
CanFlood supports multiple groups of the four data fields described above, allowing for more advanced configuration of compound vulnerability.
For example, a simple buildings model may have a single depth-damage function representing the loss as a function of depth starting from the ground level.
As all L2 models require a depth-damage function, these fields are specified on the **Data Input** tab of the **Asset Inventory** toolbox. 
A more complex model might incorporate a separate function to model the loss of the basement.
In this scenario, the model would have two function groups, one for the ground floor and one for the basement.
Using this feature, a complex multi-use multi-story building can be modelled as a single asset with multiple function groups, each representing a different floor or use type (e.g., residential, commercial, etc.).
These additional function groups are configured on the **Advanced Tab** of the **Asset Inventory** toolbox.