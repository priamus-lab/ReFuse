import collections
from datetime import timedelta
from functools import reduce
from typing import List

import fsspec
import geopandas
import intake
import numpy as np
import pandas as pd
import pystac
import rasterio
import requests
import rioxarray
from pystac_client import Client
from shapely.geometry import Polygon, shape, mapping
from shapely.geometry.base import BaseGeometry


def search_sentinel2(
        area_of_interest,
        start_date,
        end_date,
        cloud_coverage_tresh=0.05,
        collection="sentinel-s2-l2a-cogs",
        frequency=None,
):
    if frequency is not None and frequency <= 7:
        frequency = None

    catalog = Client.open("https://earth-search.aws.element84.com/v0")
    # catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

    params = {}
    if not collection:
        collection = "sentinel-s2-l2a-cogs"
    params["collections"] = collection

    # Calculate bbox (search executed using bbox)
    bounds_left, bounds_bottom, bounds_right, bounds_top = area_of_interest.bounds
    bbox = Polygon(
        [
            [bounds_left, bounds_bottom],
            [bounds_left, bounds_top],
            [bounds_right, bounds_top],
            [bounds_right, bounds_bottom],
        ]
    )
    params["intersects"] = bbox

    if start_date is not None:
        params["datetime"] = "%s/%s" % (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    params["query"] = {"eo:cloud_cover": {"lte": 100}}

    search = catalog.search(**params)

    print(f"{search.matched()} Items found")

    # organize by date
    items_by_date_dict = collections.defaultdict(list)
    for item in search.get_items():
        items_by_date_dict[item.datetime.date()].append(item)

    # check cloud coverage and area covered by date
    check_result = []

    next_date = None
    for date in items_by_date_dict:
        try:
            if (frequency is None) or (next_date is None) or (date <= next_date):
                print(f"Computing cloud coverage: {date} - {items_by_date_dict[date]}...")

                area_coverered = check_coverage(items_by_date_dict[date], area_of_interest)
                percentage_novalid_data = None
                if area_coverered:
                    mask_novalid_data, percentage_novalid_data = get_cloud_coverage(
                        items_by_date_dict[date], area_of_interest
                    )

                check_result.append(
                    {
                        "date": date,
                        "area_coverered": area_coverered,
                        "percentage_novalid_data": percentage_novalid_data,
                    }
                )

                if frequency is not None and area_coverered and percentage_novalid_data <= cloud_coverage_tresh:
                    next_date = date - timedelta(days=frequency - 3)
        except Exception as ex:
            print(f"Error computing cloud coverage: {date} - {items_by_date_dict[date]}. Exception: {ex}")

    print(check_result)

    df = pd.DataFrame.from_dict(check_result)

    good_dates = df[df.area_coverered & (df.percentage_novalid_data <= cloud_coverage_tresh)]
    print(good_dates)
    return good_dates


def download_sentinel2(
    area_of_interest,
    start_date,
    end_date,
    search_result,
    destination_path,
    collection="sentinel-s2-l2a-cogs",
    ):

    catalog = Client.open("https://earth-search.aws.element84.com/v0")
    # catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

    params = {}
    if not collection:
        collection = "sentinel-s2-l2a-cogs"
    params["collections"] = collection

    # Calculate bbox (search executed using bbox)
    bounds_left, bounds_bottom, bounds_right, bounds_top = area_of_interest.bounds
    bbox = Polygon(
        [
            [bounds_left, bounds_bottom],
            [bounds_left, bounds_top],
            [bounds_right, bounds_top],
            [bounds_right, bounds_bottom],
        ]
    )
    params["intersects"] = bbox

    if start_date is not None:
        params["datetime"] = "%s/%s" % (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    params["query"] = {"eo:cloud_cover": {"lte": 100}}

    search = catalog.search(**params)

    print(f"{search.matched()} Items found")

    # organize by date
    items_by_date_dict = collections.defaultdict(list)
    for item in search.get_items():
        items_by_date_dict[item.datetime.date()].append(item)

    for index, row in search_result.iterrows():
        try:
            date = row["date"]
            percentage_novalid_data = row["percentage_novalid_data"]

            print(f"Download for: {date} - {items_by_date_dict[date]}...")

            # Download assets
            assets_list = ["visual", "B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12", "SCL"]
            for asset_key in assets_list:
                # Save asset to Geotiff
                path_to_save_full = destination_path + "/{year}/{month}/{day}".format(
                    year=date.year, month=date.month, day=date.day
                )
                filename = "{asset}_{date}.tif".format(asset=asset_key, date=date.strftime("%Y%m%d"))
                filepath_to_save = path_to_save_full + f"/{filename}"

                mosaic = get_mosaic(
                    items_by_date_dict[date], asset_key=asset_key, area_of_interest=area_of_interest
                )

                save_to_file(mosaic, filepath_to_save)

        except Exception as ex:
            print(f"Error downloading: {date} - {items_by_date_dict[date]}. Exception: {ex}")

    return destination_path


def check_coverage(items: List[pystac.Item], full_area: BaseGeometry):
    temp_area = full_area

    for item in items:
        # print("Processing item {}".format(item))
        item_geom = shape(item.geometry)
        temp_area = temp_area - item_geom

    area_covered = temp_area.is_empty
    return area_covered


def get_cloud_coverage(items, area_of_interest: BaseGeometry):
    items_by_date = items
    xarray_all_patches = []

    mosaic = get_mosaic(items, asset_key="SCL", area_of_interest=area_of_interest)

    mask_novalid_data = mosaic.isin([1, 3, 8, 9, 10])
    total_count = reduce(lambda x, y: x * y, mask_novalid_data.shape)
    no_valid_count = mask_novalid_data.sum().values.item()# #
    percentage_novalid_data = no_valid_count / total_count

    return mask_novalid_data, percentage_novalid_data


def get_mosaic(items: List[pystac.Item], asset_key: str, area_of_interest: BaseGeometry, nodataval: int = 0):
    xarray_all_patches = []

    for item in items:
        # print("Processing item {} for asset {}".format(item, asset_key))
        asset_xarray = read_sentinel2_item(item, asset_key)

        asset_xarray.rio.set_nodata(0)
        asset_clipped = asset_xarray.rio.clip([mapping(area_of_interest)], crs=4326, all_touched=True, drop=True)
        xarray_all_patches.append(asset_clipped)

    # compute a unique resolution and crs for the merge
    estimated_utm_crs_pyproj = geopandas.GeoDataFrame(
        {"geometry": [area_of_interest]}, crs="EPSG:4326"
    ).estimate_utm_crs()
    estimated_utm_crs_rio = rasterio.crs.CRS.from_user_input(estimated_utm_crs_pyproj)
    res = tuple(abs(res_val) for res_val in xarray_all_patches[0].rio.resolution())

    mosaic = rioxarray.merge.merge_arrays(
        xarray_all_patches, precision=50, nodata=nodataval, res=res, crs=estimated_utm_crs_rio
    )  # rasterio.crs.CRS.from_string("+init=epsg:4326"))

    return mosaic


def read_sentinel2_item(item: pystac.Item, asset_key: str):
    # sign href. Necessary if you use Microsoft Planetary
    # asset_href = item.assets[asset_key].href
    # signed_href = pc.sign(asset_href)
    # item.assets[asset_key].href = signed_href

    single_intake_item = intake.open_stac_item(item)
    asset_xarray = single_intake_item[asset_key](chunks=dict(band=1, y=2048, x=2048)).to_dask()
    asset_xarray.rio.set_nodata(0, inplace=True)
    attrs = {
        "nodatavals": (0,),
    }
    asset_xarray.rio.update_attrs(attrs, inplace=True)

    try:
        # Check if xarray is georeferenced properly looking for CRS attribute
        crs = None
        crs = asset_xarray.attrs["crs"]
    except KeyError as e:
        pass

    if not crs:
        # print("Catalog not georefenced")

        # Get tileInfo.json
        tileinfo = get_tile_info(item)
        # print(tileinfo)
        crs_from_tileinfo = tileinfo["tileOrigin"]["crs"]["properties"]["name"]
        origin_coordinates = tileinfo["tileOrigin"]["coordinates"]
        # print(f"origin_coordinates: {origin_coordinates}")
        gsd = get_asset_gsd(item, asset_key)
        shape = (1830 * 60 // gsd, 1830 * 60 // gsd)  # shape of a Sentinel-2 tile
        # print(f"gsd: {gsd}")
        # print(f"shape: {shape}")
        geotransform, x_coords, y_coords = generate_coordinates(
            origin_coordinates=origin_coordinates, shape=shape, gsd=gsd
        )
        # print(x_coords)
        # print(y_coords)
        # print(f"geotransform: {geotransform}")

        # assign new coordinates
        asset_xarray = asset_xarray.assign_coords({"x": x_coords, "y": y_coords})
        # set attributes
        attrs = {
            "crs": crs_from_tileinfo,
            "transform": geotransform,  # (20.0, 0.0, 499980.0, 0.0, -20.0, 5000040.0)
            "res": (gsd, gsd),
            "nodatavals": (0,),
        }
        asset_xarray.rio.update_attrs(attrs, inplace=True)

    return asset_xarray


def get_tile_info(item: pystac.Item):
    tileinfo_url = item.asset("info")["href"]
    r = requests.get(tileinfo_url)
    tileinfo = r.json()
    return tileinfo


def get_asset_gsd(item: pystac.Item, asset_key: str):
    asset_info = item.asset(asset_key)
    gsd = asset_info.get("sgd")
    if not gsd:
        # if SGD property is not defined try to understand SGD from the path
        # of the file (e.g., 'href': 's3://sentinel-s2-l2a/tiles/32/T/NQ/2018/1/2/0/R60m/B01.jp2')
        href = asset_info.get("href")
        if "10m" in href:
            gsd = 10
        elif "20m" in href:
            gsd = 20
        elif "60m" in href:
            gsd = 60

    return gsd


def generate_coordinates(origin_coordinates, shape, gsd):
    tol = 1e-15  # tolerance for deciding when a number is zero

    # RASTERIO
    # affine.Affine(a, b, c,
    #               d, e, f,
    # .              0, 0, 1)
    # GDAL
    # (c, a, b, f, d, e)

    geotransform = (origin_coordinates[0], gsd, 0, origin_coordinates[1], 0, gsd * -1)
    affine = rasterio.Affine.from_gdal(*geotransform)

    if affine.e <= tol and affine.a <= tol:
        order = -1
        step = np.array([affine.d, affine.b])
    else:
        order = 1
        step = np.array([affine.e, affine.a])

    origin = affine.f + step[0] / 2, affine.c + step[1] / 2
    end = origin[0] + step[0] * (shape[::order][0] - 1), origin[1] + step[1] * (shape[::order][1] - 1)

    start, stop = origin[0], end[0]
    # print(start, stop)
    y_coords = np.linspace(start, stop, shape[1])

    start, stop = origin[1], end[1]
    x_coords = np.linspace(start, stop, shape[0])

    geotransform_rasterio = (affine.a, affine.b, affine.c, affine.d, affine.e, affine.f)
    return geotransform_rasterio, x_coords, y_coords


def save_to_file(data, filepath):
    print(f"Saving file: {filepath}")
    with fsspec.open(filepath, mode="wb") as f:
        data.rio.to_raster(f, driver="GTiff")
