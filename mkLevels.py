#
# Generate a sorted, de-duplicated set of integer contour levels from a
# list of comma-delimited strings (as produced by argparse action="append").
#
# Jan-2022, Pat Welch, pat@mousebrains.com

import numpy as np

# Default isobath depths, in metres, used when no --contour is supplied.
DEFAULT_LEVELS = (10, 20, 50, 100, 200, 500, 1000, 2000)


def mkLevels(contours: list[str] | None) -> np.ndarray:
    if not contours:  # None or empty list
        return np.array(DEFAULT_LEVELS)

    levels = set()  # a set de-duplicates for us
    for contour in contours:
        for token in contour.split(","):
            token = token.strip()
            if not token:  # tolerate trailing/empty commas
                continue
            try:
                levels.add(int(token))
            except ValueError as e:
                raise ValueError(f"Cannot convert contour level {token!r} to an integer") from e

    if not levels:
        raise ValueError("No contour levels were provided")

    return np.array(sorted(levels))  # matplotlib requires strictly increasing
