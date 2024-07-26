import unittest
from geometry import latlon2tile

class TestLatLon2Tile(unittest.TestCase):

    def test_zero_zero_zero(self):
        # 测试经纬度为(0, 0)且zoom为0时的情况
        lon, lat, zoom = 0, 0, 0
        expected_col, expected_row = 0, 0
        col, row = latlon2tile(lon, lat, zoom)
        self.assertEqual(col, expected_col)
        self.assertEqual(row, expected_row)

    def test_zero_zero_high_zoom(self):
        # 测试经纬度为(0, 0)且zoom为一个较高值时的情况
        lon, lat, zoom = 0, 0, 18
        expected_col, expected_row = 0, 0
        col, row = latlon2tile(lon, lat, zoom)
        self.assertEqual(col, expected_col)
        self.assertEqual(row, expected_row)

    def test_extreme_lat_lon(self):
        # 测试经纬度为极端值时的情况
        lon, lat, zoom = 180, 90, 1
        expected_col, expected_row = 1, 1
        col, row = latlon2tile(lon, lat, zoom)
        self.assertEqual(col, expected_col)
        self.assertEqual(row, expected_row)

    def test_negative_lat_lon(self):
        # 测试经纬度为负值时的情况
        lon, lat, zoom = -180, -90, 1
        expected_col, expected_row = 0, 0
        col, row = latlon2tile(lon, lat, zoom)
        self.assertEqual(col, expected_col)
        self.assertEqual(row, expected_row)

    def test_edge_cases(self):
        # 测试接近边界条件的经纬度
        lon, lat, zoom = -179.9, 89.9, 1
        expected_col, expected_row = 0, 0
        col, row = latlon2tile(lon, lat, zoom)
        self.assertEqual(col, expected_col)
        self.assertEqual(row, expected_row)

        lon, lat, zoom = 179.9, -89.9, 1
        expected_col, expected_row = 1, 1
        col, row = latlon2tile(lon, lat, zoom)
        self.assertEqual(col, expected_col)
        self.assertEqual(row, expected_row)

if __name__ == '__main__':
    unittest.main()
