import os
import sys
import FreeCAD

import tools
from config_loader import load_config

Gui = FreeCAD.Gui

# Define absolute paths relative to this folder
# WBWBPath = os.path.dirname(__file__)
WBWBPath = tools.wb_dir
WBIconsPath = tools.icons_dir
# WBIconsPath = os.path.join(WBWBPath, "icons")

# Force FreeCAD's internal Python engine to see your new WaffleBaker folder files
if WBWBPath not in sys.path:
    sys.path.append(WBWBPath)


class WaffleBakerWorkBench(Gui.Workbench):
    """Create Intersectional/Laminational sheet metal dies from sheet metal 3D models."""

    global WBWBPath
    global WBIconsPath
    global load_config

    # These show up in the top selection dropdown menu
    MenuText = "Waffle Baker"
    ToolTip = "Create intersectional/laminational sheet metal dies"
    Icon = os.path.join(WBIconsPath, "waffle.png")

    def Initialize(self):
        # Dynamically import create_cube.py when the workbench switches on
        import step_to_fusion
        import align_model
        import create_cube
        import cut_cube
        import cut_and_rearrange

        load_config()

        # Must perfectly match the string in Gui.addCommand at the bottom of create_cube.py
        self.list = [
            "step_to_fusion",
            "align_model",
            "create_cube",
            "cut_cube",
            "cut_and_rearrange",
        ]

        # Build UI layout structures
        self.appendToolbar("Waffle Baker Options", self.list)
        self.appendMenu("&Waffle Baker", self.list)

        # Register icons mapping directory
        Gui.addIconPath(WBIconsPath)

    def GetClassName(self):
        return "Gui::PythonWorkbench"


# Register the workbench class into FreeCAD's core interface loop
Gui.addWorkbench(WaffleBakerWorkBench())
