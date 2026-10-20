import base64
import os
import urllib.error
import urllib.parse
import urllib.request


def query(sql, **settings):
    url = os.getenv('CLICKHOUSE_URL', 'http://localhost:8123')
    auth = f"{os.getenv('CLICKHOUSE_USER', 'student')}:{os.getenv('CLICKHOUSE_PASSWORD', 'student')}"
    request = urllib.request.Request(url + '/?' + urllib.parse.urlencode(settings),
                                     data=sql.encode(), method='POST')
    request.add_header('Authorization', 'Basic ' + base64.b64encode(auth.encode()).decode())
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read().decode()
    except urllib.error.HTTPError as error:
        raise RuntimeError(error.read().decode()) from error
