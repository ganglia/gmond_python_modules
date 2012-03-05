"""
The MIT License

Copyright (c) 2008 Gilad Raphaelli <gilad@raphaelli.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

if using < python2.5, http://code.activestate.com/recipes/523034/ works as a
pure python collections.defaultdict substitute
"""

#from collections import defaultdict
try:
    from collections import defaultdict
except:
    class defaultdict(dict):
        def __init__(self, default_factory=None, *a, **kw):
            if (default_factory is not None and
                not hasattr(default_factory, '__call__')):
                raise TypeError('first argument must be callable')
            dict.__init__(self, *a, **kw)
            self.default_factory = default_factory
        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                return self.__missing__(key)
        def __missing__(self, key):
            if self.default_factory is None:
                raise KeyError(key)
            self[key] = value = self.default_factory()
            return value
        def __reduce__(self):
            if self.default_factory is None:
                args = tuple()
            else:
                args = self.default_factory,
            return type(self), args, None, None, self.items()
        def copy(self):
            return self.__copy__()
        def __copy__(self):
            return type(self)(self.default_factory, self)
        def __deepcopy__(self, memo):
            import copy
            return type(self)(self.default_factory,
                              copy.deepcopy(self.items()))
        def __repr__(self):
            return 'defaultdict(%s, %s)' % (self.default_factory,
                                            dict.__repr__(self))

import MySQLdb

def longish(x):
	if len(x):
		try:
			return long(x)
		except ValueError:
			return longish(x[:-1])
	else:
		raise ValueError

def parse_infobright_status(infobright_status_raw):
	def sumof(status):
		def new(*idxs):
			return sum(map(lambda x: longish(status[x]), idxs))
		#new.func_name = 'sumof'  #not ok in py2.3
		return new

	infobright_status = defaultdict(int)
	infobright_status['active_transactions']

	for line in infobright_status_raw:
		istatus = line.split()

		isum = sumof(istatus)

		# SEMAPHORES
		# if "Mutex spin waits" in line:
		#	innodb_status['spin_waits'] += longish(istatus[3])
		#	innodb_status['spin_rounds'] += longish(istatus[5])

		#	innodb_status['os_waits'] += longish(istatus[8])

if __name__ == '__main__':
	from optparse import OptionParser

	parser = OptionParser()
	parser.add_option("-H", "--Host", dest="host", help="Host running mysql", default="localhost")
	parser.add_option("-u", "--user", dest="user", help="user to connect as", default="")
	parser.add_option("-p", "--password", dest="passwd", help="password", default="")
	parser.add_option("-P", "--port", dest="port", help="port", default=5029)
	(options, args) = parser.parse_args()

	try:
		conn = MySQLdb.connect(user=options.user, host=options.host, passwd=options.passwd, port=options.port)

		cursor = conn.cursor(MySQLdb.cursors.Cursor)
		cursor.execute("SHOW /*!50000 ENGINE*/ INNODB STATUS")
		innodb_status = parse_innodb_status(cursor.fetchone()[0].split('\n'))
		cursor.close()

		conn.close()
	except MySQLdb.OperationalError, (errno, errmsg):
		raise

