.. _sec01-gettingStarted:

Getting Started
==================

The following sections will help you get started using CanFlood2.
We suggest reading these sections first before reading the :ref:`User Guide <sec02-userGuide>` or the :ref:`Tutorials <sec03-tutorials>`.


.. _sec01-install:

Installation
------------

To install CanFlood2, you first need to install QGIS, then you can install CanFlood2 from the Plugin Repository.
For detailed instructions, refer to the `project README <https://github.com/NRCan/CanFlood2/tree/main?tab=readme-ov-file#installation>`_.
For best performance, ensure you have the specified version of QGIS installed.

After installation of the plugin, the |CanFlood2_icon| icon should appear on your plugins toolbar.
If you don't see the icon, first ensure the plugin is checked on the **Installed** tab of the "**Manage and Install Plugins..**" dialog, then ensure the **plugins toolbar** is enabled by right-clicking the QGIS toolbar.

.. |CanFlood2_icon| image:: /assets/logo_20210510_22x22.png
   :align: middle
   :width: 14


.. _sec01-overview:

Overviews
-----------------------
CanFlood v2 is an object-based, transparent, open-source flood risk calculation tool built for Canada's Federal Guidelines for Flood Risk Assessment.
This tool is designed to help you build, run, and evaluate a set of flood risk models from data you provide for your study area. 
The tool assumes you have a basic understanding of flood risk modelling as described in the Federal Guidelines for Flood Risk Assessment. For more information, see the documentation (or click the help button).  






.. _sec01-quick:

Quick-Start
-----------------------

To start working with CanFlood2, click the |CanFlood2_icon| to open the main dialog.


.. _fig-dialog-welcome:

.. figure:: /assets/01-dialog-welcome.png
   :alt: Welcome Tab
   :align: center
   :width: 900px

   Welcome message


Once you have collected and prepared the input data summarized on the welcome tab, the remaining tabs can be used to build, run, and evaluate your flood risk models as summarized in the following sections.

.. _sec01-projectSetup:

Project Setup
~~~~~~~~~~~~~~~~~~~~~~~

On the Project Setup tab, begin by creating a Project Database File with the **New** button.
Additional optional fields are provided to specify the study area and DEM layers.

Pressing the **Save** button will save the information you've entered so far onto the project database file.

.. _fig-dialog-projectSetup:

.. figure:: /assets/02-dialog-projectSetup.PNG
   :alt: Project Setup Tab
   :align: center
   :width: 900px

   Project Setup


.. _sec01-hazard:

Hazard
~~~~~~~~~~~~~~~~~~~~~~~

On the Hazard tab, you can specify hazard layers and metadata to configure the hazard scenario for your models.
Once your rasters are loaded into your QGIS project, click the **Refresh** button to populate the dialog, then select the layers you would like to include in the hazard scenario.
Once the layers are selected in the middle pane, use the **Populate Table** button to create an Event Metadata table of the scenario.
Finally, enter the event probabilities (and optional metadata) before again pressing **Save** to store this information in the project database file.

.. _fig-dialog-hazard:

.. figure:: /assets/03-dialog-hazard.PNG
   :alt: Hazard Tab
   :align: center
   :width: 900px

   Hazard



.. _sec01-modelSuite:

Model Suite
~~~~~~~~~~~~~~~~~~~~~~~

On the *Model Suite* tab, you can configure the models included in your analysis.
The seven receptor categories described in the Federal Guidelines for Flood Risk Assessment are included in the tool to help you organize your models.
Begin by clicking **Create Templates** to generate a model template for each receptor category.
Additional models can be added or removed using the +/- buttons.
Each model must then be configured via its respective **Configure** button, which launches the :ref:`Model Configuration <sec01-modelConfig>` dialog.

.. _fig-dialog-modelSuite:

.. figure:: /assets/04-dialog-modelSuite.PNG
   :alt: Model Suite Tab
   :align: center
   :width: 900px

   Model Suite


.. _sec01-modelConfig:

Model Configuration
~~~~~~~~~~~~~~~~~~~~~~~

Begin your model configuration by specifying the Inventory Vector Layer and its key fields:
   - **Index FieldName**: the field that uniquely identifies each feature.
   - **Elevation Type**: controls whether the values in tghe **elevation field** are absolute or relative to the DEM.
   - **tag**: the field containing the code corresponding to the damage function for that asset.
   - **scale**: the field containing the value by which the damage function result should be scaled (e.g., floor area).
   - **elevation**: the field containing the elevation or height of the asset.
   - **cap**: the field containing the maximum impact value to allow for the asset (e.g., comlete replacement cost)

.. _fig-dialog-modelConfig-AssetInventory:

.. figure:: /assets/06-dialog-MC-AssetInventory.png
   :alt: Model Configuration - Asset Inventory
   :align: center
   :width: 900px

   Model Configuration - Asset Inventory

Next, the vulnerability or damage functions associated with the asset inventory can be specified on the **Vulnerability** tab by clicking **Load From File** and selecting a CanFlood format function database.

.. _fig-dialog-modelConfig-Vulnerability:

.. figure:: /assets/07-dialog-MC-Vulnerability.png
   :alt: Model Configuration - Vulnerability
   :align: center
   :width: 900px

   Model Configuration - Vulnerability


Next the exposure parameters can be specified on the **Exposure** tab.


.. _fig-dialog-modelConfig-Exposure:

.. figure:: /assets/08-dialog-MC-Exposure.png
   :alt: Model Configuration - Exposure
   :align: center
   :width: 900px

   Model Configuration - Exposure

Finally, the EAD calculation parameters must be configured on the **Risk** tab.

.. _fig-dialog-modelConfig-Risk:

.. figure:: /assets/09-dialog-MC-Risk.png
   :alt: Model Configuration - Risk
   :align: center
   :width: 900px

   Model Configuration - Risk

Once the model is fully configured, it can be run using the **Run** button on the **Model Suite** tab.

.. _sec01-results:

Reporting
~~~~~~~~~~~~~~~~~~~~~~~

Once your model suite is configured and successfully run, the tools on the **Results** tab can be used to visualize and analyze the results.

.. _fig-dialog-results:

.. figure:: /assets/05-dialog-results.PNG
   :alt: Results Tab
   :align: center
   :width: 900px

   Results

See the :ref:`User Guide <sec02-userGuide>` and the :ref:`Tutorials <sec03-tutorials>` section to learn more.


.. _sec01-faq:

Frequently Asked Questions
--------------------------

**is CanFlood a flood risk model?**

No, it is a framework for building and running flood risk models.






