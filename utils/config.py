import requests
import json


CONFIG_FILE = 'https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json'


class Config:
    def __init__(self):
        self.config = requests.get(CONFIG_FILE).json()


if __name__ == '__main__':
    config = Config()
    print(config.config.keys())
    print(len(config.config.keys()))
