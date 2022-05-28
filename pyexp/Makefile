# Makefile for python interface for package pyexp.
# gopy build -output=pyexp -vm=python3 github.com/natun-ai/natun/pkg/pyexp

GOCMD=go
GOBUILD=$(GOCMD) build -mod=mod
PYTHON=python3

# get the CC and flags used to build python:
GCC = $(shell $(GOCMD) env CC)
CFLAGS = $(shell $(GOCMD) run ../hack/bindutil.go -vm $(PYTHON) -cflags)
LDFLAGS = $(shell $(GOCMD) run ../hack/bindutil.go -vm $(PYTHON) -ldflags)

#MACOS
GCC_ARGS = -dynamiclib
LIBEXT = .so

# LINUX
# CFLAGS = -I/usr/include/python3.9
# LDFLAGS = -L/usr/lib -lpython3.9 -lcrypt -lpthread -ldl  -lutil -lm -lm
# GCC_ARGS =
# LIBEXT = .so

# WINDOWS
# GCC_ARGS = -shared
# LIBEXT = .pyd


## Install dependencies
LOCALBIN ?= $(shell pwd)/bin
$(LOCALBIN): ## Ensure that the directory exists
	mkdir -p $(LOCALBIN)

GOPY ?= $(LOCALBIN)/gopy
.PHONY: gopy
gopy: $(GOPY) ## Download gopy locally if necessary.
$(GOPY):
	GOBIN=$(LOCALBIN) go install github.com/go-python/gopy@master

GOIMPORTS ?= $(LOCALBIN)/goimports
.PHONY: goimports
goimports: $(GOIMPORTS) ## Download goimports locally if necessary.
$(GOIMPORTS):
    GOBIN=$(LOCALBIN) go install golang.org/x/tools/cmd/goimports@master

.DEFAULT_GOAL := help


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

.PHONY: info
info:
	@echo "Info"
	@echo "GOCMD: $(GOCMD)"
	@echo "GOBUILD: $(GOBUILD)"
	@echo "PYTHON: $(PYTHON)"
	@echo "GCC: $(GCC)"
	@echo "CFLAGS: $(CFLAGS)"
	@echo "LDFLAGS: $(LDFLAGS)"
	@echo "GCC_ARGS: $(GCC_ARGS)"
	@echo "LIBEXT: $(LIBEXT)"

##@ Build

.PHONY: all
all: gen build ## Build all targets.

.PHONY: gen
gen: gopy ## Generate the python interface.
	$(GOPY) gen -no-make -vm=python3 github.com/natun-ai/natun/pkg/pyexp

.PHONY: build
build: goimports ## Build the python interface.
	# build target builds the generated files -- this is what gopy build does..
	#
	# this will otherwise be built during go build and may be out of date
	- rm pyexp.c
	# goimports is needed to ensure that the imports list is valid
	$(GOIMPORTS) -w pyexp.go
	# generate pyexp_go$(LIBEXT) from pyexp.go -- the cgo wrappers to go functions
	$(GOBUILD) -buildmode=c-shared -o pyexp_go$(LIBEXT) pyexp.go
	# use pybindgen to build the pyexp.c file which are the CPython wrappers to cgo wrappers..
	# note: pip install pybindgen to get pybindgen if this fails
	$(PYTHON) build.py
	# build the _pyexp$(LIBEXT) library that contains the cgo and CPython wrappers
	# generated pyexp.py python wrapper imports this c-code package

	# windows-only sed hack here to fix pybindgen declaration of PyInit
    # sed -i "s/ PyInit_/ __declspec(dllexport) PyInit_/g" pyexp.c

	$(GCC) pyexp.c $(GCC_ARGS) pyexp_go$(LIBEXT) -o _pyexp$(LIBEXT) $(CFLAGS) $(LDFLAGS) -fPIC --shared -w
	


