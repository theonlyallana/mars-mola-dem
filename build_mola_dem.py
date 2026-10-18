import os
import subprocess

from osgeo import gdal

# Enable GDAL exceptions for better error messages
gdal.UseExceptions()

# Directory containing the four PDS3 .lbl files and the .img files they name.
# An empty string means the current working directory.
directory = r""

# 64 pixel/degree MEGDR topography tiles (map scale 0.926 km/pixel).
# These are not the 128 pixel/degree (~463 m) products.
lbl_files = [
    "megt90n000gb.lbl",  # 90 N to 0, 0 E to 180 E
    "megt90n180gb.lbl",  # 90 N to 0, 180 E to 360 E
    "megt00n000gb.lbl",  # 0 to 90 S, 0 E to 180 E
    "megt00n180gb.lbl",  # 0 to 90 S, 180 E to 360 E
]

lbl_paths = [os.path.join(directory, f) for f in lbl_files]
missing = [path for path in lbl_paths if not os.path.isfile(path)]
if missing:
    raise FileNotFoundError(
        "Missing PDS3 label(s):\n  "
        + "\n  ".join(missing)
        + "\nPlace megt90n000gb, megt90n180gb, megt00n000gb, and megt00n180gb "
        "(.lbl and the .img named by each label) in this directory, or set "
        "`directory` above. An empty directory means the current working directory."
    )

vrt_output = os.path.join(directory, "mars_mola_global.vrt")
tif_output = os.path.join(directory, "mars_mola_global_64ppd.tif")

# MOLA MEGDR labels are one pixel off. GDAL documents this correction:
# https://gdal.org/en/stable/drivers/raster/pds.html
gdal.SetConfigOption("PDS_SampleProjOffset_Shift", "-0.5")
gdal.SetConfigOption("PDS_LineProjOffset_Shift", "-0.5")

# Cubic resampling is used only if a source has to be resampled. These four
# tiles share one resolution, so the mosaic is normally a direct composite.
vrt_options = gdal.BuildVRTOptions(
    resampleAlg="cubic",
    addAlpha=False,
    srcNodata=None,
    VRTNodata=None,
)

vrt_ds = gdal.BuildVRT(vrt_output, lbl_paths, options=vrt_options)
if vrt_ds is None:
    raise RuntimeError(
        "Failed to build VRT. Check that each .lbl can read its .img file."
    )

# Keep the Mars simple-cylindrical CRS from the PDS labels. Replacing it with
# EPSG:4326 leaves metre coordinates labelled as WGS84 degrees.
projection = vrt_ds.GetProjection()
geotransform = vrt_ds.GetGeoTransform()
x_size = vrt_ds.RasterXSize
y_size = vrt_ds.RasterYSize

vrt_ds.FlushCache()
vrt_ds = None
print(f"Virtual mosaic created: {vrt_output}")
print(f"   Size: {x_size} x {y_size}")
print(f"   Geotransform: {geotransform}")
print(f"   CRS: {projection}")

# MEGDR topography samples are already integer metres (scale 1, offset 0).
# unscale=True does not promote these tiles to Float32.
translate_options = gdal.TranslateOptions(
    format="GTiff",
    creationOptions=[
        "COMPRESS=DEFLATE",
        "PREDICTOR=2",
        "ZLEVEL=9",
        "TILED=YES",
        "BIGTIFF=YES",
    ],
    noData=None,
    unscale=True,
)

print("Materializing to GeoTIFF...")
tif_ds = gdal.Translate(tif_output, vrt_output, options=translate_options)
if tif_ds is None:
    raise RuntimeError("Failed to create GeoTIFF.")

band = tif_ds.GetRasterBand(1)
dtype = gdal.GetDataTypeName(band.DataType)
nodata = band.GetNoDataValue()
tif_ds.FlushCache()
tif_ds = None
print(f"Global Mars MOLA DEM created: {tif_output}")
print(f"   Data type: {dtype}. Elevations are MEGDR topography in metres relative to the areoid.")
print(f"   NoData: {nodata}")

print("Adding external overviews...")
overview = subprocess.run(
    [
        "gdaladdo",
        "-ro",
        "--config",
        "COMPRESS_OVERVIEW",
        "DEFLATE",
        "--config",
        "PREDICTOR_OVERVIEW",
        "2",
        tif_output,
        "2",
        "4",
        "8",
        "16",
        "32",
        "64",
    ],
    check=False,
)
if overview.returncode != 0:
    raise RuntimeError(
        f"gdaladdo exited {overview.returncode}. "
        "The GeoTIFF was written, but the external overviews were not."
    )

print("All done!")
