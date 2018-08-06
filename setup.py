import os
import re
import sys
import platform
import subprocess

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
from distutils.version import LooseVersion

from torch.utils.cpp_extension import include_paths


class CMakeExtension(Extension):
    def __init__(self, name, sourcedir=''):
        kwargs = dict()

        include_dirs = kwargs.get('include_dirs', [])
        include_dirs += include_paths()
        kwargs['include_dirs'] = include_dirs

        if sys.platform == 'win32':
            library_dirs = kwargs.get('library_dirs', [])
            library_dirs += library_paths()
            kwargs['library_dirs'] = library_dirs

            libraries = kwargs.get('libraries', [])
            libraries.append('caffe2')
            libraries.append('_C')
            kwargs['libraries'] = libraries

        kwargs['language'] = 'c++'

        Extension.__init__(self, name, sources=[], **kwargs)
        self.sourcedir = os.path.abspath(sourcedir)


def add_torch_deps(ext):
    here = os.path.dirname(os.path.abspath(__file__))
    cmake = os.path.join(here, 'CMakeLists.txt')

    with open(cmake, 'a') as cm:
        for d in ext.include_dirs:
            print("include_directories({})".format(d), file=cm)
        print("target_compile_definitions(cmake_example PUBLIC -DTORCH_EXTENSION_NAME=cmake_example)", file=cm)
        print("target_compile_definitions(cmake_example PUBLIC -D_GLIBCXX_USE_CXX11_ABI=0)", file=cm)



class CMakeBuild(build_ext):
    def run(self):
        try:
            out = subprocess.check_output(['cmake', '--version'])
        except OSError:
            raise RuntimeError("CMake must be installed to build the following extensions: " +
                               ", ".join(e.name for e in self.extensions))

        if platform.system() == "Windows":
            cmake_version = LooseVersion(re.search(r'version\s*([\d.]+)', out.decode()).group(1))
            if cmake_version < '3.1.0':
                raise RuntimeError("CMake >= 3.1.0 is required on Windows")

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))
        cmake_args = ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + extdir,
                      '-DPYTHON_EXECUTABLE=' + sys.executable]

        cfg = 'Debug' if self.debug else 'Release'
        build_args = ['--config', cfg]

        if platform.system() == "Windows":
            cmake_args += ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}'.format(cfg.upper(), extdir)]
            if sys.maxsize > 2**32:
                cmake_args += ['-A', 'x64']
            build_args += ['--', '/m']
        else:
            cmake_args += ['-DCMAKE_BUILD_TYPE=' + cfg]
            build_args += ['--', '-j2']


        env = os.environ.copy()
        env['CXXFLAGS'] = '{} -DVERSION_INFO=\\"{}\\"'.format(env.get('CXXFLAGS', ''),
                                                              self.distribution.get_version())
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)

        add_torch_deps(ext)

        subprocess.check_call(['cmake', ext.sourcedir] + cmake_args, cwd=self.build_temp, env=env)
        subprocess.check_call(['cmake', '--build', '.'] + build_args, cwd=self.build_temp)


setup(
    name='cmake_example',
    version='0.0.1',
    author='Dean Moldovan',
    author_email='dean0x7d@gmail.com',
    description='A test project using pybind11 and CMake',
    long_description='',
    ext_modules=[CMakeExtension('cmake_example')],
    cmdclass=dict(build_ext=CMakeBuild),
    zip_safe=False,
)
