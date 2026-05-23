import FreeCAD as App
from dataclasses import dataclass
import math


class Const:
    SHEET_THICKNESS = 2.0
    MIN_INTERVAL = 2.0
    OUTER_INTERVAL = 10.0  # represents the distance from the edge.
    CUBE_Z_OFFSET = -32.0
    CUBE_TOTAL_HEIGHT = 100.0
    SAFETY_HEIGHT = 5.0  # NOTE: DECIDE UPPER DIE INTER SECTION Z HEIGHT. IT SHOULD LARGER THAN TARGET SHEET METAL'S THICKNESS IN STEP FILE.
    CUBE_MARGIN = 10.0
    DXF_SHEETS_GAP = 10.0


@dataclass
class sheet_info:
    bounder_length: int
    vec: App.Base.Vector
    sheet_num: int = 0
    thickness: float = Const.SHEET_THICKNESS
    interval: float = 0
    outer_interval: float = Const.OUTER_INTERVAL

    def __post_init__(self):
        offset_length = self.bounder_length - self.outer_interval
        number: float = (offset_length + Const.MIN_INTERVAL) / (
            Const.MIN_INTERVAL + self.thickness
        )
        self.sheet_num = math.floor(number)
        full_interval = (offset_length - self.thickness * self.sheet_num) / (
            self.sheet_num - 1
        )
        self.interval = round(full_interval, 1)
        App.Console.PrintMessage(f"  sheet_info: {self}\n")
