from StringIO import StringIO
from flup.client.fcgi_app import FCGIApp, Record, FCGI_BEGIN_REQUEST, struct, \
    FCGI_BeginRequestBody, FCGI_RESPONDER, FCGI_BeginRequestBody_LEN, FCGI_STDIN, \
    FCGI_DATA, FCGI_STDOUT, FCGI_STDERR, FCGI_END_REQUEST
from pprint import pprint
import urllib2
import json

### bitten by a php-fpm bug: http://bugs.php.net/bug.php?id=53618&thanks=4
class FCGIAppMalformedHeaderWorkAround(FCGIApp):
    def __call__(self, environ, start_response):
        # For sanity's sake, we don't care about FCGI_MPXS_CONN
        # (connection multiplexing). For every request, we obtain a new
        # transport socket, perform the request, then discard the socket.
        # This is, I believe, how mod_fastcgi does things...

        sock = self._getConnection()

        # Since this is going to be the only request on this connection,
        # set the request ID to 1.
        requestId = 1

        # Begin the request
        rec = Record(FCGI_BEGIN_REQUEST, requestId)
        rec.contentData = struct.pack(FCGI_BeginRequestBody, FCGI_RESPONDER, 0)
        rec.contentLength = FCGI_BeginRequestBody_LEN
        rec.write(sock)

        # Filter WSGI environ and send it as FCGI_PARAMS
        if self._filterEnviron:
            params = self._defaultFilterEnviron(environ)
        else:
            params = self._lightFilterEnviron(environ)
        # TODO: Anything not from environ that needs to be sent also?
        self._fcgiParams(sock, requestId, params)
        self._fcgiParams(sock, requestId, {})

        # Transfer wsgi.input to FCGI_STDIN
        content_length = int(environ.get('CONTENT_LENGTH') or 0)
        while True:
            chunk_size = min(content_length, 4096)
            s = environ['wsgi.input'].read(chunk_size)
            content_length -= len(s)
            rec = Record(FCGI_STDIN, requestId)
            rec.contentData = s
            rec.contentLength = len(s)
            rec.write(sock)

            if not s: break

        # Empty FCGI_DATA stream
        rec = Record(FCGI_DATA, requestId)
        rec.write(sock)

        # Main loop. Process FCGI_STDOUT, FCGI_STDERR, FCGI_END_REQUEST
        # records from the application.
        result = []
        while True:
            inrec = Record()
            inrec.read(sock)
            if inrec.type == FCGI_STDOUT:
                if inrec.contentData:
                    result.append(inrec.contentData)
                else:
                    # TODO: Should probably be pedantic and no longer
                    # accept FCGI_STDOUT records?
                    pass
            elif inrec.type == FCGI_STDERR:
                # Simply forward to wsgi.errors
                environ['wsgi.errors'].write(inrec.contentData)
            elif inrec.type == FCGI_END_REQUEST:
                # TODO: Process appStatus/protocolStatus fields?
                break

        # Done with this transport socket, close it. (FCGI_KEEP_CONN was not
        # set in the FCGI_BEGIN_REQUEST record we sent above. So the
        # application is expected to do the same.)
        sock.close()

        result = ''.join(result)

        # Parse response headers from FCGI_STDOUT
        status = '200 OK'
        headers = []
        pos = 0
        while True:
            eolpos = result.find('\n', pos)
            if eolpos < 0: break
            line = result[pos:eolpos - 1]
            pos = eolpos + 1

            # strip in case of CR. NB: This will also strip other
            # whitespace...
            line = line.strip()

            # Empty line signifies end of headers
            if not line: break

            # TODO: Better error handling
            if  ':' not in line:
                continue

            header, value = line.split(':', 1)
            header = header.strip().lower()
            value = value.strip()

            if header == 'status':
                # Special handling of Status header
                status = value
                if status.find(' ') < 0:
                    # Append a dummy reason phrase if one was not provided
                    status += ' FCGIApp'
            else:
                headers.append((header, value))

        result = result[pos:]

        # Set WSGI status, headers, and return result.
        start_response(status, headers)
        return [result]

def start_response(status, headers):
    pass

if __name__ == '__main__':
    app = FCGIAppMalformedHeaderWorkAround(connect=('localhost', 49000), filterEnviron=False)

    env = {
        'QUERY_STRING': 'json',
        'REQUEST_METHOD': 'GET',
        'SCRIPT_FILENAME': '/status',
        'SCRIPT_NAME': '/status',
        'wsgi.input': StringIO(),
        'wsgi.errors': StringIO()
    }

    result = app(environ=env, start_response=start_response)

    if len(result) <= 0:
        raise Exception('Cannot parse response: ' + result)

    status = json.loads(result[0])

