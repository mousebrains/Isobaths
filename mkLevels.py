#
# Generate a set of contour levels from a comma deliminated list
#
# Jan-2022, Pat Welch, pat@mousebrains

import numpy as np
import sys

def mkLevels(contours:tuple[str]) -> np.array:
    if contours is None:
        return np.array([10, 20, 50, 100, 200, 500, 1000, 2000])

    levels = []
    for contour in contours:
        for level in contour.split(","):
            try:
                levels.append(int(level))
            except Exception as e:
                print("Unable to convert", level, "to a floating point number")
                print(str(e))
                sys.exit(1)
    return np.array(sorted(levels))
