"""
不同坐标和位置之间的转换
"""
import math


def latlon2tile(lon, lat, zoom):
    """
    将经纬度转换为瓦片坐标
    :param lat: 纬度
    :param lon: 经度
    :param zoom: 级别
    :return: 瓦片坐标
    """
    col = math.floor(((lon + 180) / 360) * math.pow(2, zoom))
    row = math.floor(
        ((1 -
          math.log(
              math.tan((lat * math.pi) / 180) +
              1 / math.cos((lat * math.pi) / 180)
          ) /
          math.pi) /
         2) *
        math.pow(2, zoom)
    )
    return col, row


def getExtent(x1, y1, x2, y2, z):
    pos1x, pos1y = wgs_to_tile(x1, y1, z)
    pos2x, pos2y = wgs_to_tile(x2, y2, z)
    Xframe = pixls_to_mercator(
        {"LT": (pos1x, pos1y), "RT": (pos2x, pos1y), "LB": (pos1x, pos2y), "RB": (pos2x, pos2y), "z": z})
    for i in ["LT", "LB", "RT", "RB"]:
        Xframe[i] = mercator_to_wgs(*Xframe[i])
    # for i in ["LT", "LB", "RT", "RB"]:
    #     Xframe[i] = gcj_to_wgs(*Xframe[i])
    return Xframe


if __name__ == '__main__':
    print(latlon2tile(108.952727786758032, 28.183458510102184, 18))

