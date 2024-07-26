import io
import multiprocessing
import os
import time
from threading import Thread
import PIL.Image as pil
import cv2
import numpy as np
import pandas as pd

from loguru import logger
from osgeo import gdal, osr
from retrying import retry

from utils.geometry import *
from wayback import *


def get_url(api, level, col, row):
    return api.format(level=level, col=col, row=row)


def get_urls(x2, y2, x1, y1, level, url):
    lenx = x1 - x2  #+ 1  # row, 纬度维度
    leny = y1 - y2  #+ 1  # col, 经度维度
    return [get_url(url, level, y, x) for y in range(y1 - leny, y1) for x in range(x1 - lenx, x1)]


@retry(stop_max_attempt_number=3,  # 最大重试次数
       wait_fixed=1000)
def download(url):
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/88.0.4324.150 Safari/537.36 Edg/88.0.705.68'
    }
    try:
        response = requests.get(url, headers=header)
        # time.sleep(0.1)
        content = response.content
        return content
    except Exception:
        raise Exception(f"Download failed, {url}")


class Downloader(Thread):
    # multiple threads downloader
    def __init__(self, index, count, urls, datas):
        # index represents the number of threads
        # count represents the total number of threads
        # urls represents the list of URLs nedd to be downloaded
        # datas represents the list of data need to be returned.
        super().__init__()
        self.urls = urls
        self.datas = datas
        self.index = index
        self.count = count

    def run(self):
        for i, url in enumerate(self.urls):
            if i % self.count != self.index:
                continue
            self.datas[i] = download(url)


def download_tiles(urls, multi=10):
    url_len = len(urls)
    datas = [None] * url_len
    if multi < 1 or multi > 20 or not isinstance(multi, int):
        raise Exception("multi of Downloader shuold be int and between 1 to 20.")
    tasks = [Downloader(i, multi, urls, datas) for i in range(multi)]
    for i in tasks:
        i.start()
    for i in tasks:
        i.join()
    return datas


def merge_tiles(datas, x2, y2, x1, y1):
    lenx = x2 - x1  #+ 1
    leny = y2 - y1  #+ 1
    outpic = pil.new('RGBA', (leny * 256, lenx * 256))
    for i, data in enumerate(datas):
        picio = io.BytesIO(data)
        small_pic = pil.open(picio)
        # y, x = lenx - i // leny - 1, i % leny
        x, y = i // lenx, i % lenx
        outpic.paste(small_pic, (x * 256, y * 256))
    return outpic


def saveTiff(r, g, b, gt, filePath):
    fname_out = filePath
    driver = gdal.GetDriverByName('GTiff')
    # Create a 3-band dataset
    dset_output = driver.Create(fname_out, r.shape[1], r.shape[0], 3, gdal.GDT_Byte)
    dset_output.SetGeoTransform(gt)
    try:
        proj = osr.SpatialReference()
        proj.ImportFromEPSG(4326)
        dset_output.SetSpatialRef(proj)
    except:
        print("Error: Coordinate system setting failed")
    dset_output.GetRasterBand(1).WriteArray(r)
    dset_output.GetRasterBand(2).WriteArray(g)
    dset_output.GetRasterBand(3).WriteArray(b)
    dset_output.FlushCache()
    dset_output = None


@retry(stop_max_attempt_number=3,
       wait_fixed=10000)
def main(left, top, right, bottom, zoom, save_tiff, item_url):
    pos1y, pos1x = latlon2tile(left, top, zoom)
    pos2y, pos2x = latlon2tile(right, bottom, zoom)
    logger.info(f"正在下载的瓦片范围: {pos1x}:{pos2x}, {pos1y}:{pos2y}")
    try:
        urls = get_urls(pos1x, pos1y, pos2x, pos2y, zoom, item_url)
        urls_group = [urls[i:i + math.ceil(len(urls) / multiprocessing.cpu_count())] for i in
                      range(0, len(urls), math.ceil(len(urls) / multiprocessing.cpu_count()))]
        pool = multiprocessing.Pool(multiprocessing.cpu_count())
        results = pool.map(download_tiles, urls_group)
        pool.close()
        pool.join()
        result = [x for j in results for x in j]
        # Combine downloaded tile maps into one map
        outpic = merge_tiles(result, pos2x, pos2y, pos1x, pos1y)
        outpic = outpic.convert('RGB')
    except:
        logger.error(f"merge failed, {left}_{top}__{right}__{bottom}, 重试中...")
        raise Exception(f"merge failed, {left}_{top}__{right}__{bottom}")
    r, g, b = cv2.split(np.array(outpic))
    # Get the spatial information of the four corners of the merged map and use it for outputting
    extent = getExtent(left, top, right, bottom, zoom)
    gt = (extent["LT"][0], (extent["RB"][0] - extent["LT"][0]) / r.shape[1], 0, extent["LT"][1], 0,
          (extent["LB"][1] - extent["LT"][1]) / r.shape[0])
    saveTiff(r, g, b, gt, save_tiff)


if __name__ == "__main__":
    position_file = ""   # 记录地理位置，经纬度范围的txt文件

    csv_file = ''    # 记录经纬度信息的csv文件
    zoom = 1      # zoom的大小
    city = 'xx'
    config = Config()
    wayback_list = None
    data = pd.read_csv(csv_file)

    # for pos in get_latlon_from_txt(position_file):
    # left, top, bottom, right = pos
    for index, row in data.iterrows():
        name = row['name']
        left, top, right, bottom = row['min_x'], row['max_y'], row['max_x'], row['min_y']
        if wayback_list is None:
            wayback_list = get_wayback_item_list(config.config, lat=top, lon=left, zoom=zoom)

        for wayback in wayback_list:
            logger.info(f"正在下载的(拍摄)日期: {wayback.capture_date}")
            save_dir = os.path.join(city, wayback.capture_date, )
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            file_path = f'{name[:-4]}_{left}_{top}-{right}_{bottom}_zoom_{zoom}.tif'

            save_tiff = os.path.join(save_dir, file_path)
            if os.path.exists(save_tiff):
                continue
            try:
                main(left, top, right, bottom, zoom, save_tiff, wayback.item_url)
            except Exception as e:
                raise Exception(f"下载瓦片失败, {left}_{top}__{right}__{bottom}, {e}")
            break
        break
