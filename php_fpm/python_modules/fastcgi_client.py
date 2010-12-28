from StringIO import StringIO
from flup.client.fcgi_app import FCGIApp, Record, FCGI_BEGIN_REQUEST
from pprint import pprint
import urllib2

def start_response(status, headers):
    print "status:"
    pprint(status)

    print "\nheaders:"
    pprint(headers)

    print "\n"

if __name__ == '__main__':
    app = FCGIApp(connect=('localhost', 49000), filterEnviron=False)

    env = {
        'QUERY_STRING': 'json',
        'REQUEST_METHOD': 'GET',
        'SCRIPT_FILENAME': '/status',
        'wsgi.input': StringIO()
    }

    result = app(environ=env, start_response=start_response)

    print "Data:"
    pprint(result)

