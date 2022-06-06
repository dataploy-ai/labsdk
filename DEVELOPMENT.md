# How to develop this module

## Prerequisites:
1. Golang 1.18+
2. Gopy & Goimports installed on $GOBIN
   1. `go install github.com/go-python/gopy@master`
   2. `golang.org/x/tools/cmd/goimports@latest`
3. For building the wheels, you need to have the following packages installed:
   1. build
   2. wheel
   3. auditwheel - linux
   4. delocate - macos
   5. delvewheel - windows

## Compiling the module locally
You can utilize the Make script to compile the module:

```$ make cleanup build-wheel build-repair PYTHON=python3```

The makefile is basically sugaring the `setup.py` and mimicking the CI.

## Compile the go extension while developing
If you need to recompile the PyExp library, it's recommended to use GoPy make script. Just run:

```$ gopy build --name="pyexp" --output natun/pyexp --vm=python3 github.com/natun-ai/natun/pkg/pyexp```

You can also place a `replace` directive in the `go.mod` file to replace the upstream Natun repo
with your local version. Don't forget to remove it before committing your changes!