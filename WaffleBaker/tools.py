import os
import FreeCAD

# current_dir = os.path.dirname(__file__)
# if current_dir not in sys.path:
#     sys.path.append(current_dir)

# Define absolute paths relative to this folder
# these value should be path str
wb_dir = os.path.dirname(__file__)
ui_path = os.path.join(wb_dir, "Resources/")
config_dir = FreeCAD.getUserConfigDir()
icons_dir = os.path.join(wb_dir, "icons")
