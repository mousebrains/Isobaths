#! /usr/bin/env python3
#
# Generate isobaths from a GEBCO gridded bathymetry NetCDF file.
#
# Jan-2022, Pat Welch, pat@mousebrains.com

import sys

from isobaths import main

if __name__ == "__main__":
    sys.exit(main(default_variable="elevation", source="GEBCO"))
