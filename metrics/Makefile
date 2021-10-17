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
# Simple makefile to build metrics quickly and reproducibly
#
# Common uses:
# - installing metrics: `make install INSTALL_DIR=$HOME/go/bin`
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
# PATH:=$(shell . metrics/build/setup-go.sh && echo "$${PATH}")
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
# INSTALL_DIR?=$(shell metrics/build/goinstalldir.sh)
# the output binary name, overridden when cross compiling
METRICS_BINARY_NAME?=metrics

OS=$(shell uname)
ifeq ($(shell uname),Darwin)
    JQ_PATH=jq-1.5/jq-osx-amd64
else
    JQ_PATH=jq-1.5/jq-linux64
endif

# build flags for the metrics binary
# - reproducible builds: -trimpath and -ldflags=-buildid=
# - smaller binaries: -w (trim debugger data, but not panics)
# - metadata: -X=... to bake in git commit
# KIND_BUILD_FLAGS?=-trimpath -ldflags="-buildid= -w -X=sigs.k8s.io/metrics/pkg/cmd/metrics/version.GitCommit=$(COMMIT)"
################################################################################
# ================================= Building ===================================
# standard "make" target -> builds
all: build
# builds metrics in a container, outputs to $(OUT_DIR)
metrics: requirements bigquery bigquery-test
	echo "Completed Metrics!"

requirements:
	pip3 install certifi chardet idna python-dateutil pytz ruamel.yaml requests six urllib3

	if [ ! -d "jq-1.5" ]; then ./get_jq.sh; fi

bigquery:
	python3 bigquery.py

bigquery-test:
	python3 bigquery_test.py --jq $(JQ_PATH)

# alias for building metrics
build: metrics
# use: make install INSTALL_DIR=/usr/local/bin
# install: build
# 	$(INSTALL) -d $(INSTALL_DIR)
# 	$(INSTALL) "$(OUT_DIR)/$(METRICS_BINARY_NAME)" "$(INSTALL_DIR)/$(METRICS_BINARY_NAME)"
################################################################################
# ================================= Testing ====================================
# unit tests (hermetic)
# unit:
# 	MODE=unit metrics/make-rules/test.sh
# integration tests
# integration:
# 	MODE=integration metrics/make-rules/test.sh
# all tests
# test:
# 	docker run $(METRICS_BINARY_NAME)
################################################################################
# ================================= Cleanup ====================================
# standard cleanup target
clean:
	rm -rf jq-1.5
################################################################################
# ============================== Auto-Update ===================================
# update generated code, gofmt, etc.
# update:
# 	metrics/make-rules/update/all.sh
# update generated code
# generate:
# 	metrics/make-rules/update/generated.sh
# gofmt
# gofmt:
# 	metrics/make-rules/update/gofmt.sh
################################################################################
# ================================== Linting ===================================
# run linters, ensure generated code, etc.
# verify:
# 	metrics/make-rules/verify/all.sh
# code linters
# lint:
# 	metrics/make-rules/verify/lint.sh
# shell linter
# shellcheck:
# 	metrics/make-rules/verify/shellcheck.sh
#################################################################################
.PHONY: all metrics build install unit clean update generate gofmt verify lint shellcheck