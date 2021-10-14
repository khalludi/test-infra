# Copyright 2019 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Old-skool build tools.
# Simple makefile to build hack quickly and reproducibly
#
# Common uses:
# - installing hack: `make install INSTALL_DIR=$HOME/go/bin`
# - building: `make build`
# - cleaning up and starting over: `make clean`
#
################################################################################
# ========================== Capture Environment ===============================
# get the repo root and output path
REPO_ROOT:=${CURDIR}
OUT_DIR=$(REPO_ROOT)/bin
# record the source commit in the binary, overridable
COMMIT?=$(shell git rev-parse HEAD 2>/dev/null)
################################################################################
# ========================= Setup Go With Gimme ================================
# go version to use for build etc.
# setup correct go version with gimme
# PATH:=$(shell . hack/build/setup-go.sh && echo "$${PATH}")
# go1.9+ can autodetect GOROOT, but if some other tool sets it ...
# GOROOT:=
# enable modules
# GO111MODULE=on
# disable CGO by default for static binaries
# CGO_ENABLED=0
# export PATH GOROOT GO111MODULE CGO_ENABLED
# work around broken PATH export
# SPACE:=$(subst ,, )
# SHELL:=env PATH=$(subst $(SPACE),\$(SPACE),$(PATH)) $(SHELL)
################################################################################
# ============================== OPTIONS =======================================
# install tool
# INSTALL?=install
# install will place binaries here, by default attempts to mimic go install
# INSTALL_DIR?=$(shell hack/build/goinstalldir.sh)
# the output binary name, overridden when cross compiling
HACK_BINARY_NAME?=hack
# build flags for the hack binary
# - reproducible builds: -trimpath and -ldflags=-buildid=
# - smaller binaries: -w (trim debugger data, but not panics)
# - metadata: -X=... to bake in git commit
# KIND_BUILD_FLAGS?=-trimpath -ldflags="-buildid= -w -X=sigs.k8s.io/hack/pkg/cmd/hack/version.GitCommit=$(COMMIT)"
################################################################################
# ================================= Building ===================================
# standard "make" target -> builds
# all: build
# builds hack in a container, outputs to $(OUT_DIR)
hack:
	docker build -t $(HACK_BINARY_NAME) .
# alias for building hack
build: hack
# use: make install INSTALL_DIR=/usr/local/bin
# install: build
# 	$(INSTALL) -d $(INSTALL_DIR)
# 	$(INSTALL) "$(OUT_DIR)/$(HACK_BINARY_NAME)" "$(INSTALL_DIR)/$(HACK_BINARY_NAME)"
################################################################################
# ================================= Testing ====================================
# unit tests (hermetic)
# unit:
# 	MODE=unit hack/make-rules/test.sh
# integration tests
# integration:
# 	MODE=integration hack/make-rules/test.sh
# all tests
test:
	docker run $(HACK_BINARY_NAME)
################################################################################
# ================================= Cleanup ====================================
# standard cleanup target
clean:
	docker rmi -f $(HACK_BINARY_NAME)
################################################################################
# ============================== Auto-Update ===================================
# update generated code, gofmt, etc.
# update:
# 	hack/make-rules/update/all.sh
# update generated code
# generate:
# 	hack/make-rules/update/generated.sh
# gofmt
# gofmt:
# 	hack/make-rules/update/gofmt.sh
################################################################################
# ================================== Linting ===================================
# run linters, ensure generated code, etc.
# verify:
# 	hack/make-rules/verify/all.sh
# code linters
# lint:
# 	hack/make-rules/verify/lint.sh
# shell linter
# shellcheck:
# 	hack/make-rules/verify/shellcheck.sh
#################################################################################
.PHONY: all hack build install unit clean update generate gofmt verify lint shellcheck