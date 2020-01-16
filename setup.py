import distutils.ccompiler
import distutils.sysconfig
import os
import platform
import tempfile

from setuptools import setup, find_packages, Extension

from pathlib import Path
thisDir = Path(__file__).parent.absolute()

setupArgs = {"use_scm_version": {
        "write_to": thisDir / "ijson" / "version.py",
        "write_to_template": 'version = "{version}"\n',
    }
}

# Check if the yajl library + headers are present
# We don't use compiler.has_function because it leaves a lot of files behind
# without properly cleaning up
def yajl_present():

    compiler = distutils.ccompiler.new_compiler(verbose=1)
    distutils.sysconfig.customize_compiler(compiler) # CC, CFLAGS, LDFLAGS, etc

    fname = tempfile.mktemp(".c", "yajl_version")
    try:
        with open(fname, "wt") as f:
            f.write('''
            #include <yajl/yajl_version.h>
            int main(int args, char **argv)
            {
            #if YAJL_MAJOR != 2
                fail to compile
            #else
                yajl_version();
            #endif
                return 0;
            }
            ''')

        try:
            objs = compiler.compile([fname])
            compiler.link_shared_lib(objs, 'a', libraries=["yajl"])
            return True
        finally:
            os.remove(compiler.library_filename('a', lib_type='shared'))
            for obj in objs:
                os.remove(obj)

    except:
        return False
    finally:
        if os.path.exists(fname):
            os.remove(fname)

# Conditional compilation of the yajl_c backend
if platform.python_implementation() == 'CPython':
    if yajl_present():
        yajl_ext = Extension('ijson.backends._yajl2',
                             language='c',
                             sources = ['ijson/backends/_yajl2.c'],
                             libraries = ['yajl'])
        setupArgs['ext_modules'] = [yajl_ext]

setup(**setupArgs)
