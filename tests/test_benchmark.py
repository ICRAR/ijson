import os
import subprocess
import sys
import tempfile

from tests.test_base import JSON


class TestBenchmark:

    def _do_test_benchmark(self, method="basic_parse", multiple_values=True, extra_args=None):
        # Use python backend to ensure multiple_values works
        if multiple_values:
            env = dict(os.environ)
            env['IJSON_BACKEND'] = 'python'
        # Ensure printing works on the subprocess in Windows
        # by using utf-8 on its stdout
        if sys.platform == 'win32':
            env = dict(os.environ)
            env['PYTHONIOENCODING'] = 'utf-8'
        cmd = [sys.executable, '-m', 'ijson.benchmark', '-m', method, '-p', '', '-s', '1']
        if multiple_values:
            cmd.append('-M')
        if extra_args:
            cmd += extra_args
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        out, err = proc.communicate()
        status = proc.wait()
        assert 0 == status, "out:\n%s\nerr:%s" % (out.decode('utf-8'), err.decode('utf-8'))

    def _test_benchmark(self, method):
        self._do_test_benchmark(method)
        self._do_test_benchmark(method, extra_args=['-c'])
        self._do_test_benchmark(method, extra_args=['-a'])

    def test_basic_parse(self):
        self._test_benchmark('basic_parse')

    def test_parse(self):
        self._test_benchmark('parse')

    def test_kvitems(self):
        self._test_benchmark('kvitems')

    def test_items(self):
        self._test_benchmark('items')

    def test_list(self):
        self._do_test_benchmark(extra_args=['-l'])

    def test_more_iterations(self):
        self._do_test_benchmark(extra_args=['-I', '1'])
        self._do_test_benchmark(extra_args=['-I', '2'])
        self._do_test_benchmark(extra_args=['-I', '3'])

    def test_input_files(self):
        fd, fname = tempfile.mkstemp()
        os.write(fd, JSON)
        os.close(fd)
        try:
            self._do_test_benchmark(extra_args=[fname])
            self._do_test_benchmark(extra_args=[fname, fname])
        finally:
            os.unlink(fname)
