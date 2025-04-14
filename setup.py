import glob
import os
import shutil
import tempfile

from setuptools import setup, Extension
from setuptools._distutils import ccompiler
from setuptools._distutils import sysconfig

setupArgs = {}

# Check if the yajl library + headers are present
# We don't use compiler.has_function because it leaves a lot of files behind
# without properly cleaning up
def yajl_present():

    compiler = ccompiler.new_compiler(verbose=1)
    sysconfig.customize_compiler(compiler) # CC, CFLAGS, LDFLAGS, etc

    yajl_version_test_file = tempfile.NamedTemporaryFile(suffix=".c", prefix="yajl_version", delete=False)
    try:
        yajl_version_test_file.write(b'''
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
        yajl_version_test_file.close()

        try:
            objs = compiler.compile([yajl_version_test_file.name])
            compiler.link_shared_lib(objs, 'a', libraries=["yajl"])
            return True
        finally:
            os.remove(compiler.library_filename('a', lib_type='shared'))
            for obj in objs:
                os.remove(obj)

    except:
        return False
    finally:
        os.remove(yajl_version_test_file.name)


def patch_yajl_sources():
    """Make yajl sources ready for direct compilation against them"""
    # cp cextern/yajl -R $yajl_sources_copy
    # mkdir $yajl_sources_copy/yajl
    # cp $yajl_sources_copy/src/api/*.h $yajl_sources_copy/yajl
    patched_sources = os.path.join(tempfile.mkdtemp(), 'yajl')
    shutil.copytree(os.path.join('cextern', 'yajl'), patched_sources)
    headers_original = os.path.join(patched_sources, 'src', 'api')
    headers_copy = os.path.join(patched_sources, 'yajl')
    shutil.copytree(headers_original, headers_copy)
    return patched_sources


extra_sources = []
extra_include_dirs = []
libs = ['yajl']
embed_yajl = os.environ.get('IJSON_EMBED_YAJL', None) == '1'
if not embed_yajl:
    have_yajl = yajl_present()
else:
    yajl_sources = patch_yajl_sources()
    extra_sources = sorted(glob.glob(os.path.join(yajl_sources, 'src', '*.c')))
    extra_sources.remove(os.path.join(yajl_sources, 'src', 'yajl_version.c'))
    extra_include_dirs = [yajl_sources, os.path.join(yajl_sources, 'src')]
    libs = []
build_yajl_default = '1' if embed_yajl or have_yajl else '0'
build_yajl = os.environ.get('IJSON_BUILD_YAJL2C', build_yajl_default) == '1'
if build_yajl:
    yajl_ext = Extension('ijson.backends._yajl2',
                         language='c',
                         sources=sorted(glob.glob('src/ijson/backends/ext/_yajl2/*.c')) + extra_sources,
                         include_dirs=['src/ijson/backends/ext/_yajl2'] + extra_include_dirs,
                         libraries=libs,
                         depends=glob.glob('src/ijson/backends/ext/_yajl2/*.h'))
    setupArgs['ext_modules'] = [yajl_ext]

setup(**setupArgs)
