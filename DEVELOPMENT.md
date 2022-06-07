# How to develop this module

## Prerequisites:
1. Golang 1.18+
2. Gopy & Goimports installed on $GOBIN
   1. `go install github.com/go-python/gopy@master`
   2. `go install golang.org/x/tools/cmd/goimports@latest`
3. PyBindGen installed - `pip install pybindgen`
4. For building the wheels, you need to have the following packages installed:
   1. build
   2. wheel
   3. auditwheel - linux
   4. delocate - macos
   5. delvewheel - windows

It's recommended to use Python3.7 since this is the lowest version we support.

## Enable "Developer mode"
Set the environment variable `NATUN_DEV` to `1`

## Compiling the module locally
You can utilize the Make script to compile the module:

```$ make cleanup build-wheel repair-wheel PYTHON=python3```

The makefile is basically sugaring the `setup.py` and mimicking the CI.

## Compile the go extension while developing
If you need to recompile the PyExp library, it's recommended to use GoPy make script. Just run:

```$ make cleanup local-build PHYTHON=python3```

You can also place a `replace` directive in the `go.mod` file to replace the upstream Natun repo
with your local version. Don't forget to remove it before committing your changes!