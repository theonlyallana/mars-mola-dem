# Global Mars MOLA DEM

This repository contains one script, `build_mola_dem.py`, that mosaics four
NASA PDS MOLA MEGDR topography tiles into a global GeoTIFF. It does not
download the tiles, and the GeoTIFF is not stored here. There is no test
suite and no magnetic-field or MAVEN analysis.

## Data

The script reads these four PDS3 topography labels, plus the `.img` file named
by each label:

- `megt90n000gb` — 90°N to 0°, 0°E to 180°E
- `megt90n180gb` — 90°N to 0°, 180°E to 360°E
- `megt00n000gb` — 0° to 90°S, 0°E to 180°E
- `megt00n180gb` — 0° to 90°S, 180°E to 360°E

They are the 64 pixel/degree MEGDR topography tiles (filename resolution
letter `G`). The PDS label gives `MAP_SCALE = 0.926 <KM/PIXEL>`. They are not
the 128 pixel/degree products, whose map scale is about 463 m/pixel and whose
names use resolution letter `H`.

Dataset: `MGS-M-MOLA-5-MEGDR-L3-V1.0`, NASA PDS Geosciences Node.

- Product page: https://pds-geosciences.wustl.edu/missions/mgs/megdr.html
- PDS3 64 pixel/degree directory: https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg064/

The node’s product page now also points at a PDS4 bundle. This script opens
the PDS3 `.lbl` files with GDAL’s PDS driver.

## What the script does

1. Sets `PDS_SampleProjOffset_Shift` and `PDS_LineProjOffset_Shift` to `-0.5`
   before opening the labels. That is GDAL’s documented correction for the
   one-pixel offset in MOLA MEGDR labels
   (https://gdal.org/en/stable/drivers/raster/pds.html).
2. Builds `mars_mola_global.vrt` with `gdal.BuildVRT`. `resampleAlg` is
   `cubic`, which applies only if a source has to be resampled. These four
   tiles have the same resolution. In the run below, sampled pixels in the
   GeoTIFF matched the source tiles, so those samples were not resampled.
3. Leaves the coordinate system that the PDS driver reads from the label: a
   Mars simple-cylindrical projection on a sphere of radius 3396 km, central
   meridian 180°, coordinates in metres. It does not assign EPSG:4326.
4. Writes `mars_mola_global_64ppd.tif` with `gdal.Translate`
   (`COMPRESS=DEFLATE`, `PREDICTOR=2`, `ZLEVEL=9`, `TILED=YES`,
   `BIGTIFF=YES`, `unscale=True`). The topography samples are already signed
   16-bit metres (`UNIT = METER`, scale 1, offset 0). With GDAL 3.8.4,
   `unscale=True` does not change them to Float32.
5. Runs `gdaladdo -ro` to add external overviews at levels 2, 4, 8, 16, 32,
   and 64. If `gdaladdo` is missing or fails, the script stops with an error
   after the GeoTIFF has been written. The overview file is
   `mars_mola_global_64ppd.tif.ovr`.

One run with GDAL 3.8.4 produced a 23040×11520 mosaic, pixel size 926 m,
Int16, projected centre 0 m, 0 m. Elevations ran from -8199 m to 21218 m,
which is the range stated in the PDS label. GDAL records NoData as -32768;
no sample in that mosaic had that value. `gdalinfo` reported the west edge
at 0°1′20.70″E, the east edge at 0°1′20.70″W, and the north and south edges
at 89°59′19.65″. Each edge falls inside the nominal frame: about 1′21″ short
of the prime meridian on both sides (about 2′41″ short of 360° altogether)
and about 40″ short of each pole. That comes from the label map scale of
0.926 km/pixel on a 3396 km sphere. The GeoTIFF was 211 MB and the overview
file was 90 MB. Those sizes are for that run, not a guaranteed file size.

`*.tif`, `*.vrt`, and `*.ovr` are listed in `.gitignore`.

## Install

The script imports `osgeo` and runs the `gdaladdo` executable. On Ubuntu
24.04:

```bash
sudo apt-get install gdal-bin python3-gdal
python3 -c "from osgeo import gdal; print(gdal.__version__)"
```

That installed GDAL 3.8.4 here, including the PDS driver. Use `python3`. A
bare `python` command is not provided by that package.

Do not install this project with `pip install -r requirements.txt`. There is
no `requirements.txt`. The PyPI `gdal` package builds from source and fails
without a matching GDAL development install (`gdal-config` was not found).
NumPy is not used.

## Run

`directory` in `build_mola_dem.py` is empty, so inputs and outputs use the
current working directory. They are not resolved from the script’s own path.
The script looks up the lowercase label names above.

With the eight PDS files in the current directory:

```bash
python3 /path/to/build_mola_dem.py
```

From a checkout of this repository, after placing those files next to the
script:

```bash
python3 build_mola_dem.py
```

Set `directory` if the tiles should be read from somewhere other than the
current directory. Without the labels, the script raises `FileNotFoundError`
and does not write an output.

## Figure

`mars_global_topography.jpg` is a 630×316 JPEG already in the repository. The
script does not create it. The file has no caption, scale bar, color bar, or
grid, and it is not a measured output of the mosaic.

## Licence

This repository does not include a licence.

## Author

Andrew Allan
