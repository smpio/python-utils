import urllib.parse


def is_absolute(url):
    return bool(urllib.parse.urlparse(url).netloc)
