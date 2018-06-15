import urllib.parse


def is_url(url):
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc, result.path])
    except Exception:
        return False


def is_absolute(url):
    return bool(urllib.parse.urlsplit(url).netloc)
