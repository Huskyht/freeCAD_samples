import os
import sys
import FreeCAD

Gui = FreeCAD.Gui

# Define absolute paths relative to this folder
WBWBPath = os.path.dirname(__file__)
WBIconsPath = os.path.join(WBWBPath, "icons")

# Force FreeCAD's internal Python engine to see your new WaffleBaker folder files
if WBWBPath not in sys.path:
    sys.path.append(WBWBPath)


class WaffleBakerWorkBench(Gui.Workbench):
    """Create Intersectional/Laminational sheet metal dies from sheet metal 3D models."""

    # These show up in the top selection dropdown menu
    MenuText = "Waffle Baker"
    ToolTip = "Create intersectional/laminational sheet metal dies"
    Icon = os.path.join(WBIconsPath, "waffle.png")

    def Initialize(self):
        # Dynamically import create_cube.py when the workbench switches on
        import create_cube_cmd

        # Must perfectly match the string in Gui.addCommand at the bottom of create_cube.py
        self.list = ["create_cube_cmd"]

        # Build UI layout structures
        self.appendToolbar("Waffle Baker Options", self.list)
        self.appendMenu("&Waffle Baker", self.list)

        # Register icons mapping directory
        Gui.addIconPath(WBIconsPath)

    def GetClassName(self):
        return "Gui::PythonWorkbench"


# Register the workbench class into FreeCAD's core interface loop
Gui.addWorkbench(WaffleBakerWorkBench())
