import os.path
from dataclasses import dataclass
import json
import re
import urllib.parse
from datetime import datetime

import requests
from loguru import logger


@dataclass
class WayBackItem:
    release_num: int
    release_date: str
    item_url: str
    meta_url: str
    capture_date: str


def get_wayback_item_list(config, lat, lon, zoom, cache='wayback_cache.json'):
    wayback_list = []
    idx = 1
    date_list = []
    # 如果缓存文件存在，从缓存读取
    if os.path.exists(cache):
        logger.debug(f'存在缓存文件{cache}, 从缓存文件读取wayback')
        with open(cache, 'r') as f:
            datas = json.load(f)
            for data in datas:
                release_num = data['releaseNum']
                release_date = data['releaseDate']
                item_url = data['itemURL']
                meta_url = data['metadataLayerUrl']
                capture_date = data['captureDate']
                wayback_list.append(WayBackItem(
                    release_num=release_num,
                    release_date=release_date,
                    item_url=item_url,
                    meta_url=meta_url,
                    capture_date=capture_date)
                )
    else:
        cache_data = []
        for release_num, data in config.items():
            logger.debug(f'读取第{idx}个release num: {release_num}')
            idx += 1
            date_str = data['itemTitle']
            release_date = get_release_date(date_str)
            item_url = data['itemURL']
            meta_url = data['metadataLayerUrl']
            features = get_capture_date(meta_url, lon, lat, zoom).get('features', [])
            if not features:
                continue
            capture_datetime = features[0]['attributes']['SRC_DATE2']
            capture_date_str = datetime.fromtimestamp(capture_datetime / 1000)
            capture_date = capture_date_str.strftime('%Y-%m-%d')
            if capture_date in date_list:
                continue
            date_list.append(capture_date)
            wayback_list.append(WayBackItem(
                release_num=release_num,
                release_date=release_date,
                item_url=item_url,
                meta_url=meta_url,
                capture_date=capture_date

            ))
            cache_data.append({
                'releaseNum': release_num,
                'releaseDate': release_date,
                'itemURL': item_url,
                'metadataLayerUrl': meta_url,
                'captureDate': capture_date
            })
        with open(cache, 'w') as fp:
            json.dump(cache_data, fp)

    # 按capture_date排序
    wayback_list = sorted(wayback_list, key=lambda x: x.capture_date)
    return wayback_list


def get_capture_date(meta_url, longitude, latitude, zoom):
    source_date = 'SRC_DATE2'
    source_provider = 'NICE_DESC'
    source_name = 'SRC_DESC'
    resolution = 'SAMP_RES'
    accuracy = 'SRC_ACC'

    # 构造outFields的字符串
    outFields = ','.join([source_date, source_provider, source_name, resolution, accuracy])

    # 构造geometry的JSON字符串
    geometry_dict = {
        'spatialReference': {'wkid': 4326},
        'x': longitude,
        'y': latitude,
    }
    geometry_json = json.dumps(geometry_dict)

    # 创建查询参数的字典
    query_params = {
        'f': 'json',
        'where': '1=1',
        'outFields': outFields,
        'geometry': geometry_json,
        'returnGeometry': 'false',
        'geometryType': 'esriGeometryPoint',
        'spatialRel': 'esriSpatialRelIntersects',
    }

    encoded_params = urllib.parse.urlencode(query_params)

    # 如果需要完整的URL，可以这样构造（假设base_url是你的基础URL
    layer_id = get_layer_id(zoom)
    base_url = f'{meta_url}/{layer_id}/query'
    full_url = f"{base_url}?{encoded_params}"
    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                            'Chrome/89.0.4389.90 Safari/537.36'}
    rsp = requests.get(full_url, headers=header)
    if rsp.status_code == 200:
        data = rsp.json()
        return data
    raise Exception(f'解析capture日期失败: {rsp.text}')


def get_release_date(date):
    """
    获取release date
    :param date: 日期字符串，eg: 'World Imagery (Wayback 2014-02-20)'
    :return:
    """
    pattern = r'\b\d{4}-\d{2}-\d{2}\b'
    result = re.search(pattern, date)
    if result:
        return result.group()
    raise DateParseError(f'不合法的日期字符串: {date}')


def get_layer_id(zoom):
    """
    获取layer ID
    :param zoom:
    :return:
    """
    max_zoom = 23
    min_zoom = 10
    layer_id4_min_zoom = max_zoom - min_zoom
    layer_id = max_zoom - zoom
    if layer_id > layer_id4_min_zoom:
        return layer_id4_min_zoom
    return layer_id


class DateParseError(Exception):
    pass


if __name__ == '__main__':
    meta_url = 'https://metadata.maptiles.arcgis.com/arcgis/rest/services/World_Imagery_Metadata_2022_r15/MapServer'
    print(get_capture_date(meta_url, 108.952727786758032,28.183458510102184, 18))
