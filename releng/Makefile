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
# Simple makefile to build releng quickly and reproducibly
#
# Common uses:
# - installing releng: `make install INSTALL_DIR=$HOME/go/bin`
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
# PATH:=$(shell . releng/build/setup-go.sh && echo "$${PATH}")
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
# INSTALL_DIR?=$(shell releng/build/goinstalldir.sh)
# the output binary name, overridden when cross compiling
RELENG_BINARY_NAME?=releng

CONFIG_FORKER_BIN=../bazel-bin/releng/config-forker/config-forker_/config-forker
CONFIG_ROTATOR_BIN=../bazel-bin/releng/config-rotator/config-rotator_/config-rotator
GENERATE_TESTS_BIN=../bazel-bin/releng/generate_tests

YAML_CONFIG_PATH=test_config.yaml
OUTPUT_DIR=../config/jobs/kubernetes/generated/
TEST_GRID_OUTPUT_PATH=../config/testgrids/generated-test-config.yaml
# build flags for the releng binary
# - reproducible builds: -trimpath and -ldflags=-buildid=
# - smaller binaries: -w (trim debugger data, but not panics)
# - metadata: -X=... to bake in git commit
# KIND_BUILD_FLAGS?=-trimpath -ldflags="-buildid= -w -X=sigs.k8s.io/releng/pkg/cmd/releng/version.GitCommit=$(COMMIT)"
################################################################################
# ================================= Building ===================================
# standard "make" target -> builds
all: build
# builds releng in a container, outputs to $(OUT_DIR)
releng: requirements generate_tests generate_tests_test prepare_release_branch
	echo "All Done!"

requirements:
	pip3 install ruamel.yaml sh

generate_tests:	
	python3 generate_tests.py --yaml-config-path $(YAML_CONFIG_PATH) --output-dir $(OUTPUT_DIR) --testgrid-output-path $(TEST_GRID_OUTPUT_PATH)
	
generate_tests_test:
	python3 generate_tests_test.py

prepare_release_branch:
	bazel build //releng/config-forker //releng/config-rotator //releng:generate_tests
	python3 prepare_release_branch.py $(CONFIG_ROTATOR_BIN) $(CONFIG_FORKER_BIN) $(GENERATE_TESTS_BIN)

# alias for building releng
build: releng
# use: make install INSTALL_DIR=/usr/local/bin
# install: build
# 	$(INSTALL) -d $(INSTALL_DIR)
# 	$(INSTALL) "$(OUT_DIR)/$(RELENG_BINARY_NAME)" "$(INSTALL_DIR)/$(RELENG_BINARY_NAME)"
################################################################################
# ================================= Testing ====================================
# unit tests (hermetic)
# unit:
# 	MODE=unit releng/make-rules/test.sh
# integration tests
# integration:
# 	MODE=integration releng/make-rules/test.sh
# all tests
# test:
# 	docker run $(RELENG_BINARY_NAME)
################################################################################
# ================================= Cleanup ====================================
# standard cleanup target
# clean:
# 	docker rmi -f $(releng_BINARY_NAME)
################################################################################
# ============================== Auto-Update ===================================
# update generated code, gofmt, etc.
# update:
# 	releng/make-rules/update/all.sh
# update generated code
# generate:
# 	releng/make-rules/update/generated.sh
# gofmt
# gofmt:
# 	releng/make-rules/update/gofmt.sh
################################################################################
# ================================== Linting ===================================
# run linters, ensure generated code, etc.
# verify:
# 	releng/make-rules/verify/all.sh
# code linters
# lint:
# 	releng/make-rules/verify/lint.sh
# shell linter
# shellcheck:
# 	releng/make-rules/verify/shellcheck.sh
#################################################################################
.PHONY: all releng build install unit clean update generate gofmt verify lint shellcheck