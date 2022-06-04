import os
import re
import shutil
import sys
from subprocess import check_output

import setuptools
from setuptools.command.build_ext import build_ext as _build_ext
from setuptools.glob import glob

with open("./README.md", "r") as fh:
    long_description = fh.read()


class BuildGoPy(_build_ext):
    """Custom command to build extension from Go source files"""

    def ensure_go(self):
        """Ensure that the go compiler is available"""
        try:
            check_output(['go', 'version'])
        except OSError:
            raise RuntimeError('Go compiler not found')

    gobin = f"{os.getcwd()}/bin"

    def install_binaries(self):
        self.ensure_go()

        env = os.environ.copy()
        env["GOBIN"] = self.gobin

        if not os.path.exists(self.gobin):
            os.mkdir("bin")
        if not os.path.isfile(f"{self.gobin}/gopy"):
            check_output(["go", "install", "github.com/go-python/gopy@master"], env=env)
        if not os.path.isfile(f"{self.gobin}/goimports"):
            check_output(["go", "install", "golang.org/x/tools/cmd/goimports@master"], env=env)

    def ldflags(self) -> str:
        """Determine the correct link flags.  This attempts compiles similar
        to how autotools does feature detection.
        """

        # windows gcc does not support linking with unresolved symbols
        if sys.platform == 'win32':
            major, minor = sys.version_info.major, sys.version_info.minor
            return ' '.join([f'-L{p}' for p in self.library_dirs] + [f"-lpython{major}{minor}"])
        if sys.platform == 'darwin':
            return '-Wl,-undefined,dynamic_lookup'
        if sys.platform == 'linux':
            return '-Wl,--unresolved-symbols=ignore-all'
        raise RuntimeError('Unsupported platform: {}'.format(sys.platform))

    def build_extension(self, ext) -> None:
        self.ensure_go()
        self.install_binaries()

        base_path = os.path.abspath("/".join(ext.name.split(".")))
        if os.path.exists(f"{base_path}"):
            shutil.rmtree(f"{base_path}")

        pkg = os.path.basename(ext.sources[0])
        if "package_name" in ext.__dict__:
            pkg = ext.package_name

        # Creating the gopy from the package
        check_output([f"{self.gobin}/gopy", "gen", "--name", pkg,
                      "--output", base_path, "--no-make", "--vm", sys.executable] + ext.sources)

        # Fix wrong flags
        ldflags = self.ldflags()
        cflags = ' '.join([f'-I{p}' for p in self.compiler.include_dirs])
        with open(f'{base_path}/{pkg}.go', 'r+') as f:
            code = f.read()
            if sys.platform == 'win32':
                ldflags = ldflags.replace('\\', '/')
                cflags = cflags.replace('\\', '/')
            code = re.sub(r"^#cgo LDFLAGS: .*$", f"#cgo LDFLAGS: {ldflags}", code, flags=re.MULTILINE)
            code = re.sub(r"^#cgo CFLAGS: .*$", f"#cgo CFLAGS: {cflags}", code, flags=re.MULTILINE)
            f.seek(0)
            f.write(code)
            f.truncate()
            f.close()

        check_output([f"{self.gobin}/goimports", "-w", f'{base_path}/{pkg}.go'])

        so_ext = "so"
        if sys.platform == "win32":
            so_ext = "pyd"
        if sys.platform == "darwin":
            so_ext = "dylib"

        # Build the go package
        go_ext = f"lib{pkg}_impl"
        env = os.environ.copy()
        if sys.platform == "darwin":
            env["CGO_LDFLAGS"] = f"-Wl,-dylib -Wl,-install_name,{base_path}/{go_ext}.{so_ext}"

        check_output(["go", "build",
                      "-buildmode", "c-shared", "-o", f"{go_ext}.{so_ext}",
                      "-ldflags", "-s -w",
                      f'{pkg}.go'], cwd=base_path, env=env)

        # telling the linker where's the so file
        self.compiler.add_include_dir(base_path)
        self.compiler.add_runtime_library_dir(base_path)
        self.compiler.add_library_dir(base_path)
        self.compiler.add_library(re.sub(r"^lib", "", go_ext))

        if sys.platform == 'darwin':
            ext.extra_link_args = ['-Wl,-rpath,{}'.format(base_path)]

        # Update the generated header file to the correct location
        with open(f'{base_path}/build.py', 'r+') as f:
            code = f.read()
            code = re.sub(r"^mod\.add_include\(.*\)$", f"mod.add_include('\"{go_ext}.h\"')", code,
                          flags=re.MULTILINE)
            f.seek(0)
            f.write(code)
            f.truncate()
            f.close()

        # PyBindGen: Generate the Python bindings
        check_output([sys.executable, "build.py"], cwd=base_path)

        # fix windows
        if sys.platform == 'win32':
            with open(f"{base_path}/{pkg}.c", "r+") as f:
                code = f.read()
                code = re.sub(r" PyInit_", " __declspec(dllexport) PyInit_", code, flags=re.MULTILINE)
                f.seek(0)
                f.write(code)
                f.truncate()

        # copy the python code
        dist = os.path.dirname(self.get_ext_fullpath(ext.name + "."))
        if not os.path.exists(dist):
            os.makedirs(dist)
        for file in glob(rf'{base_path}/*.py'):
            if os.path.basename(file) == "build.py":
                continue
            # shutil.copy(file, dist)
            self.copy_file(file, dist)

        # compile the extension
        ext.sources = [f"{base_path}/{pkg}.c"]
        ext.name = f"{ext.name}._{ext.name.split('.')[-1]}"
        _build_ext.build_extension(self, ext)


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

    ext_modules=[
        setuptools.Extension('natun.pyexp', ["github.com/natun-ai/natun/pkg/pyexp"])
    ],
    py_modules=['natun', "natun.pyexp"],
    cmdclass={'build_ext': BuildGoPy},
    zip_safe=False,

    python_requires='>=3.7, <4'
)
