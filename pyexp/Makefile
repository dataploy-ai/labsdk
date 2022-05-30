# Makefile for python interface for package pyexp.
# gopy build -output=pyexp -vm=python3 github.com/natun-ai/natun/pkg/pyexp

GOCMD ?= go
GOBUILD = $(GOCMD) build
PYTHON ?= python3

# get the CC and flags used to build python:
GCC ?= $(shell $(GOCMD) env CC)
CFLAGS ?= $(shell $(GOCMD) run ../hack/bindutil.go -vm $(PYTHON) -cflags)
LDFLAGS ?= $(shell $(GOCMD) run ../hack/bindutil.go -vm $(PYTHON) -ldflags)
GCC_ARGS ?=
LIBEXT ?= .so


EXT_PATH ?= build/_pyexp$(LIBEXT)
GOEXT_PATH ?=build/pyexp_go$(LIBEXT)
BGOEXT_LIB = $(shell basename $(GOEXT_PATH) | sed 's/\.so$$//')
EXT_DIR = $(shell dirname $(GOEXT_PATH))
GOEXT_H_PATH = $(shell basename $(GOEXT_PATH) | sed 's/\.so$$/.h/')
SED ?= sed -i

## Install dependencies
LOCALBIN ?= $(shell pwd)/bin
ifeq ($(shell $(GOCMD) env GOOS), windows)
	LOCALBIN = [WorkspacePath]/bin
endif
$(LOCALBIN): ## Ensure that the directory exists
	mkdir -p $(LOCALBIN)

GOPY ?= $(LOCALBIN)/gopy
.PHONY: gopy
gopy: $(GOPY) ## Download gopy locally if necessary.
$(GOPY):
	GOOS= GOARCH= GOBIN=$(LOCALBIN) $(GOCMD) install github.com/go-python/gopy@master


GOIMPORTS ?= $(LOCALBIN)/goimports

.PHONY: goimports
goimports: $(GOIMPORTS) ## Download goimports locally if necessary.
$(GOIMPORTS):
	GOOS= GOARCH= GOBIN=$(LOCALBIN) $(GOCMD) install golang.org/x/tools/cmd/goimports@master

.DEFAULT_GOAL := help

## Info
$(info PYTHON: $(PYTHON))
$(info GCC: $(GCC))
$(info CFLAGS: $(CFLAGS))
$(info LDFLAGS: $(LDFLAGS))
$(info GCC_ARGS: $(GCC_ARGS))
$(info LIBEXT: $(LIBEXT))
$(info GOOS: $(GOOS))
$(info GOARCH: $(GOARCH))
$(info EXT_PATH: $(EXT_PATH))
$(info GOEXT_PATH: $(GOEXT_PATH))
$(info BGOEXT_PATH: $(BGOEXT_PATH))
$(info EXT_DIR: $(EXT_DIR))
$(info GOEXT_H_PATH: $(GOEXT_H_PATH))
$(info SED: $(SED))
$(info )

##@ General

# The help target prints out all targets with their descriptions organized
# beneath their categories. The categories are represented by '##@' and the
# target descriptions by '##'. The awk commands is responsible for reading the
# entire set of makefiles included in this invocation, looking for lines of the
# file as xyz: ## something, and then pretty-format the target and help. Then,
# if there's a line with ##@ something, that gets pretty-printed as a category.
# More info on the usage of ANSI control characters for terminal formatting:
# https://en.wikipedia.org/wiki/ANSI_escape_code#SGR_parameters
# More info on the awk command:
# http://linuxcommand.org/lc3_adv_awk.php

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Build

.PHONY: gen
gen: gopy ## Generate the python interface.
	$(GOPY) gen -no-make -vm=$(PYTHON) github.com/natun-ai/natun/pkg/pyexp

.PHONY: build
build: ## Build the python interface.
ifeq ($(shell $(GOCMD) env GOOS), windows)
	$(MAKE) build-win
else ifeq ($(shell $(GOCMD) env GOOS), darwin)
	$(MAKE) build-mac
else ifeq ($(shell $(GOCMD) env GOOS), linux)
	$(MAKE) build-linux
else
	@echo "Unknown OS: $(shell $(GOCMD) env GOOS)"
endif

.PHONY: build-win
build-win: gen ## Build the Windows binary. Don't forget to set GOOS and GOARCH
	sed -i "s/ PyInit_/ __declspec(dllexport) PyInit_/g" pyexp.c
	$(MAKE) _build GCC_ARGS=-shared LIBEXT=.pyd GCC_ARGS="-shared $(shell basename $(GOEXT_PATH))" LOCALBIN=" "

.PHONY: build-mac ## Build the mac binary.
build-mac: gen ## Build the MacOS binary. Don't forget to set GOOS and GOARCH
	$(MAKE) _build LIBEXT=.so SED='sed -i ""' LDFLAGS="-Wl,-undefined,dynamic_lookup" GCC_ARGS="-L. -I$(BGOEXT_LIB)"

.PHONY: build-linux
build-linux: gen ## Build the Linux binary. Don't forget to set GOOS and GOARCH
	$(MAKE) _build LIBEXT=.so LDFLAGS="-Wl,--unresolved-symbols=ignore-all" GCC_ARGS="-L. -I$(BGOEXT_LIB)"

.PHONY: _build
_build: goimports
	$(SED) "s/^#cgo LDFLAGS: .*$$/#cgo LDFLAGS: $(LDFLAGS)/g" pyexp.go
	# this will otherwise be built during go build and may be out of date
	- rm pyexp.c
	# goimports is needed to ensure that the imports list is valid
	$(GOIMPORTS) -w pyexp.go
	# generate pyexp_go$(LIBEXT) from pyexp.go -- the cgo wrappers to go functions
	CGO_LDFLAGS="$(LDFLAGS)" CGO_CFLAGS="$(CFLAGS) -Wno-error -Wno-implicit-function-declaration -Wno-int-conversion" $(GOBUILD) -buildmode=c-shared -o $(GOEXT_PATH)  -ldflags="-s -w" pyexp.go
	# use pybindgen to build the pyexp.c file which are the CPython wrappers to cgo wrappers..
	# note: pip install pybindgen to get pybindgen if this fails
	cp build.py $(EXT_DIR)/
	$(SED) "s/^mod\.add_include\(.*\)$$/mod.add_include('\"${shell echo $(GOEXT_H_PATH) | sed 's/\//\\\//g'}\"')/" $(EXT_DIR)/build.py
	cd $(EXT_DIR) && $(PYTHON) build.py
	# build the _pyexp$(LIBEXT) library that contains the cgo and CPython wrappers
	# generated pyexp.py python wrapper imports this c-code package
	cd $(EXT_DIR) && $(GCC) pyexp.c $(GCC_ARGS) -o $(shell basename $(EXT_PATH)) $(CFLAGS) $(LDFLAGS) -fPIC --shared -w
	rm $(EXT_DIR)/build.py $(EXT_DIR)/pyexp.c

.PHONY: cleanup
cleanup:
	rm -rf $(filter-out bin,$(filter-out Makefile,$(wildcard *)))
