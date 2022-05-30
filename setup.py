import os
import sys
from distutils.errors import CompileError
from subprocess import call

import setuptools
from setuptools.command.build_ext import build_ext as _build_ext

with open("./README.md", "r") as fh:
    long_description = fh.read()


def _get_ldflags() -> str:
    """Determine the correct link flags.  This attempts compiles similar
    to how autotools does feature detection.
    """

    # windows gcc does not support linking with unresolved symbols
    if sys.platform == 'win32':  # pragma: win32 cover
        prefix = getattr(sys, 'real_prefix', sys.prefix)
        libs = os.path.join(prefix, 'libs')
        return '-L{} -lpython{}{}'.format(libs, *sys.version_info[:2])

    if sys.platform == 'darwin':
        return '-Wl,-undefined,dynamic_lookup'
    if sys.platform == 'linux':
        return '-Wl,--unresolved-symbols=ignore-all'

    raise RuntimeError('Unsupported platform: {}'.format(sys.platform))

class build_go_ext(_build_ext):
    """Custom command to build extension from Go source files"""

    def build_extension(self: _build_ext, ext: setuptools.Extension) -> None:
        ext_path = self.get_ext_fullpath(f"_{ext.name}")
        goext_path = self.get_ext_fullpath(f"{ext.name}_go")
        cflags = ' '.join([f'-I{p}' for p in self.compiler.include_dirs])
        cmd = ['make', 'build-go', f"PYTHON={sys.executable}", f"EXT_PATH={ext_path}", f"GOEXT_PATH={goext_path}",
               f"CFLAGS={cflags}", f"LDFLAGS={_get_ldflags()}"]
        out = call(cmd)
        if out != 0:
            raise CompileError('Go build failed')


setuptools.setup(
    name="natun-pysdk",
    version="0.1.0",
    author="Almog Baku",
    author_email="almog@natun.ai",
    description="",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/natun-ai/pysdk",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
    install_requires=['pandas'],

    py_modules=['pyexp'],
    ext_modules=[
        setuptools.Extension('pyexp', [])
    ],
    cmdclass={'build_ext': build_go_ext},
    zip_safe=False,

    python_requires='>=3.7, <4'
)
