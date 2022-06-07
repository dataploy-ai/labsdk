# Makefile for gopy pkg generation of python bindings to pyexp
# File is generated by gopy (will not be overwritten though)
# gopy pkg -output=example -vm=python3 github.com/natun-ai/natun/pkg/pyexp

PYTHON ?= python

## Check for Python compatibility
ifeq ($(shell which $(PYTHON)),)
$(error "PYTHON not exists! please define a correct path using PYTHON")
endif
python_version_full := $(wordlist 2,3,$(subst ., ,$(shell $(PYTHON) --version 2>&1)))
ifneq ($(word 1,${python_version_full}),3)
$(error "python version 3.7+ is required.")
endif
ifeq ($(shell test $(word 2,${python_version_full}) -lt 7; echo $$?),0)
$(error "python version 3.7+ is required")
endif


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

##@ Development

.PHONY: _verfiy-deps
_verfiy-deps:
	@echo "Verifying dependencies..."
ifeq (, $(shell which go))
	$(error "No Go compiler found in $(PATH), please install Go before compiling locally")
endif
ifeq (, $(shell which gopy))
	@echo "GoPy not found. Installing..."
	go install github.com/natun-ai/natun/pkg/gopy@master
endif
ifeq (, $(shell which goimports))
	@echo "GoImports not found. Installing..."
	go install golang.org/x/tools/cmd/goimports@latest
endif


.PHONY: local-build
local-build: _verfiy-deps ## Build the PyExp extension for local development purposes
	gopy build --name="pyexp" --output natun/pyexp --vm=$(PYTHON) github.com/natun-ai/natun/pkg/pyexp

.PHONY: cleanup
cleanup: ## Clean up the the project directory from generated files
	@echo "cleaning up..."
	rm -rf build/ dist/ natun_labsdk.egg-info/ .egg natun/pyexp repaired_wheel

##@ Distribution

.PHONY: build-wheel
build-wheel: ## Build the module for distribution as a wheel
	$(PYTHON) -m build --wheel

.PHONY: repair-wheel
repair-wheel: ## Repair the wheel
	$(eval WHEEL=$(shell ls -1t dist/*.whl | head -n1))
ifeq ($(shell go env GOOS), windows)
	delvewheel repair --add-path natun/pyexp -w repaired_wheel $(WHEEL)
else ifeq ($(shell go env GOOS), darwin)
	delocate-listdeps $(WHEEL) &&  delocate-wheel -w repaired_wheel -v $(WHEEL)
else ifeq ($(shell go env GOOS), linux)
	auditwheel repair -w repaired_wheel $(WHEEL)
else
	@echo "Unknown OS: $(shell go env GOOS)"
endif