#!/usr/bin/env bash
# Copyright 2021 The Kubernetes Authors.
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

set -o errexit
set -o nounset
set -o pipefail

dir="$(dirname "${BASH_SOURCE[0]}")"

generate_presubmit_annotations() {
  branch="${1}"
  # only display on presubmit jobs for master branch for now since
  # a dashboard cannot have multiple tabs with the same name
  if [[ "${branch}" != "master" ]]; then
    echo ""
    return
  fi
  job_name="${2}"
  cat << EOF
    annotations:
      testgrid-dashboards: provider-azure-presubmit
      testgrid-tab-name: ${job_name}
      testgrid-alert-email: kubernetes-provider-azure@googlegroups.com
      testgrid-num-columns-recent: '30'
EOF
}

# we need to define the full image URL so it can be autobumped
tmp="gcr.io/k8s-staging-test-infra/kubekins-e2e:v20211014-794b7e0910-master"
kubekins_e2e_image="${tmp/\-master/}"

for release in "$@"; do
  output="${dir}/release-${release}.yaml"
  kubernetes_version="latest"

  if [[ "${release}" == "master" ]]; then
    branch="master"
  else
    branch="release-${release}"
    kubernetes_version+="-${release}"
  fi

  cat >"${output}" <<EOF
# generated by ./config/jobs/kubernetes/sig-cloud-provider/azure/generate.sh.
presubmits:
  kubernetes/kubernetes:
  - name: pull-kubernetes-e2e-capz-azure-disk
    decorate: true
    always_run: false
    optional: true
    run_if_changed: 'azure.*\.go'
    path_alias: k8s.io/kubernetes
    branches:
      - ${branch}
    labels:
      preset-dind-enabled: "true"
      preset-kind-volume-mounts: "true"
      preset-azure-cred-only: "true"
      preset-azure-anonymous-pull: "true"
    extra_refs:
      - org: kubernetes-sigs
        repo: cluster-api-provider-azure
        base_ref: main
        path_alias: sigs.k8s.io/cluster-api-provider-azure
        workdir: true
      - org: kubernetes-sigs
        repo: azuredisk-csi-driver
        base_ref: master
        path_alias: sigs.k8s.io/azuredisk-csi-driver
    spec:
      containers:
        - image: ${kubekins_e2e_image}-master
          command:
            - runner.sh
            - ./scripts/ci-entrypoint.sh
          args:
            - bash
            - -c
            - >-
              cd \${GOPATH}/src/sigs.k8s.io/azuredisk-csi-driver &&
              make e2e-test
          env:
            - name: AZURE_STORAGE_DRIVER
              value: kubernetes.io/azure-disk # In-tree Azure disk storage class
          securityContext:
            privileged: true
          resources:
            requests:
              cpu: 1
              memory: "4Gi"
$(generate_presubmit_annotations ${branch} pull-kubernetes-e2e-capz-azure-disk)
  - name: pull-kubernetes-e2e-capz-azure-disk-vmss
    decorate: true
    always_run: false
    optional: true
    run_if_changed: 'azure.*\.go'
    path_alias: k8s.io/kubernetes
    branches:
      - ${branch}
    labels:
      preset-dind-enabled: "true"
      preset-kind-volume-mounts: "true"
      preset-azure-cred-only: "true"
      preset-azure-anonymous-pull: "true"
    extra_refs:
      - org: kubernetes-sigs
        repo: cluster-api-provider-azure
        base_ref: main
        path_alias: sigs.k8s.io/cluster-api-provider-azure
        workdir: true
      - org: kubernetes-sigs
        repo: azuredisk-csi-driver
        base_ref: master
        path_alias: sigs.k8s.io/azuredisk-csi-driver
    spec:
      containers:
        - image: ${kubekins_e2e_image}-master
          command:
            - runner.sh
            - ./scripts/ci-entrypoint.sh
          args:
            - bash
            - -c
            - >-
              cd \${GOPATH}/src/sigs.k8s.io/azuredisk-csi-driver &&
              make e2e-test
          env:
            - name: AZURE_STORAGE_DRIVER
              value: kubernetes.io/azure-disk # In-tree Azure disk storage class
            - name: EXP_MACHINE_POOL
              value: "true"
          securityContext:
            privileged: true
          resources:
            requests:
              cpu: 1
              memory: "4Gi"
$(generate_presubmit_annotations ${branch} pull-kubernetes-e2e-capz-azure-disk-vmss)
  - name: pull-kubernetes-e2e-capz-azure-file
    decorate: true
    always_run: false
    optional: true
    run_if_changed: 'azure.*\.go'
    path_alias: k8s.io/kubernetes
    branches:
      - ${branch}
    labels:
      preset-dind-enabled: "true"
      preset-kind-volume-mounts: "true"
      preset-azure-cred-only: "true"
      preset-azure-anonymous-pull: "true"
    extra_refs:
      - org: kubernetes-sigs
        repo: cluster-api-provider-azure
        base_ref: main
        path_alias: sigs.k8s.io/cluster-api-provider-azure
        workdir: true
      - org: kubernetes-sigs
        repo: azurefile-csi-driver
        base_ref: master
        path_alias: sigs.k8s.io/azurefile-csi-driver
    spec:
      containers:
        - image: ${kubekins_e2e_image}-master
          command:
            - runner.sh
            - ./scripts/ci-entrypoint.sh
          args:
            - bash
            - -c
            - >-
              kubectl apply -f templates/addons/azurefile-role.yaml &&
              cd \${GOPATH}/src/sigs.k8s.io/azurefile-csi-driver &&
              make e2e-test
          env:
            - name: AZURE_STORAGE_DRIVER
              value: kubernetes.io/azure-file # In-tree Azure file storage class
          securityContext:
            privileged: true
          resources:
            requests:
              cpu: 1
              memory: "4Gi"
$(generate_presubmit_annotations ${branch} pull-kubernetes-e2e-capz-azure-file)
  - name: pull-kubernetes-e2e-capz-azure-file-vmss
    decorate: true
    always_run: false
    optional: true
    run_if_changed: 'azure.*\.go'
    path_alias: k8s.io/kubernetes
    branches:
      - ${branch}
    labels:
      preset-dind-enabled: "true"
      preset-kind-volume-mounts: "true"
      preset-azure-cred-only: "true"
      preset-azure-anonymous-pull: "true"
    extra_refs:
      - org: kubernetes-sigs
        repo: cluster-api-provider-azure
        base_ref: main
        path_alias: sigs.k8s.io/cluster-api-provider-azure
        workdir: true
      - org: kubernetes-sigs
        repo: azurefile-csi-driver
        base_ref: master
        path_alias: sigs.k8s.io/azurefile-csi-driver
    spec:
      containers:
        - image: ${kubekins_e2e_image}-master
          command:
            - runner.sh
            - ./scripts/ci-entrypoint.sh
          args:
            - bash
            - -c
            - >-
              kubectl apply -f templates/addons/azurefile-role.yaml &&
              cd \${GOPATH}/src/sigs.k8s.io/azurefile-csi-driver &&
              make e2e-test
          env:
            - name: AZURE_STORAGE_DRIVER
              value: kubernetes.io/azure-file # In-tree Azure file storage class
            - name: EXP_MACHINE_POOL
              value: "true"
          securityContext:
            privileged: true
          resources:
            requests:
              cpu: 1
              memory: "4Gi"
$(generate_presubmit_annotations ${branch} pull-kubernetes-e2e-capz-azure-file-vmss)
  - name: pull-kubernetes-e2e-capz-conformance
    decorate: true
    always_run: false
    optional: true
    run_if_changed: 'azure.*\.go'
    path_alias: k8s.io/kubernetes
    branches:
      - ${branch}
    labels:
      preset-dind-enabled: "true"
      preset-kind-volume-mounts: "true"
      preset-azure-cred-only: "true"
      preset-azure-anonymous-pull: "true"
    extra_refs:
    - org: kubernetes-sigs
      repo: cluster-api-provider-azure
      base_ref: main
      path_alias: sigs.k8s.io/cluster-api-provider-azure
      workdir: true
    spec:
      containers:
      - image: ${kubekins_e2e_image}-master
        command:
        - runner.sh
        - ./scripts/ci-conformance.sh
        securityContext:
          privileged: true
        resources:
          requests:
            cpu: 1
            memory: "4Gi"
        env:
        - name: KUBETEST_CONF_PATH
          value: /home/prow/go/src/sigs.k8s.io/cluster-api-provider-azure/test/e2e/data/kubetest/conformance-fast.yaml
        - name: CONFORMANCE_NODES
          value: "25"
$(generate_presubmit_annotations ${branch} pull-kubernetes-e2e-capz-conformance)
  - name: pull-kubernetes-e2e-capz-ha-control-plane
    decorate: true
    decoration_config:
      timeout: 4h
    always_run: false
    optional: true
    path_alias: k8s.io/kubernetes
    branches:
      - ${branch}
    labels:
      preset-dind-enabled: "true"
      preset-kind-volume-mounts: "true"
      preset-azure-cred-only: "true"
      preset-azure-anonymous-pull: "true"
    extra_refs:
    - org: jackfrancis #TODO change back to kubernetes-sigs
      repo: cluster-api-provider-azure
      base_ref: capz-ha-control-plane-tests #TODO change back to main
      path_alias: sigs.k8s.io/cluster-api-provider-azure
      workdir: true
    spec:
      containers:
      - image: ${kubekins_e2e_image}-master
        command:
        - runner.sh
        - ./scripts/ci-conformance.sh
        securityContext:
          privileged: true
        resources:
          requests:
            cpu: 1
            memory: "4Gi"
        env:
        - name: KUBETEST_CONF_PATH
          value: /home/prow/go/src/sigs.k8s.io/cluster-api-provider-azure/test/e2e/data/kubetest/conformance.yaml
        - name: CONFORMANCE_NODES
          value: "1"
        - name: CONFORMANCE_CONTROL_PLANE_MACHINE_COUNT
          value: "3"
$(generate_presubmit_annotations ${branch} pull-kubernetes-e2e-capz-ha-control-plane)
periodics:
- interval: 3h
  name: capz-conformance-${release/./-}
  decorate: true
  decoration_config:
    timeout: 3h
  labels:
    preset-dind-enabled: "true"
    preset-kind-volume-mounts: "true"
    preset-azure-cred-only: "true"
  extra_refs:
  - org: kubernetes-sigs
    repo: cluster-api-provider-azure
    base_ref: main
    path_alias: sigs.k8s.io/cluster-api-provider-azure
  spec:
    containers:
    - image: ${kubekins_e2e_image}-master
      command:
      - runner.sh
      - ./scripts/ci-conformance.sh
      env:
      - name: E2E_ARGS
        value: "-kubetest.use-ci-artifacts"
      - name: KUBERNETES_VERSION
        value: "${kubernetes_version}"
      - name: CONFORMANCE_WORKER_MACHINE_COUNT
        value: "2"
      securityContext:
        privileged: true
      resources:
        requests:
          cpu: 1
          memory: "4Gi"
  annotations:
    testgrid-dashboards: provider-azure-${release}-signal
    testgrid-tab-name: capz-conformance
    testgrid-alert-email: kubernetes-provider-azure@googlegroups.com
    testgrid-num-columns-recent: '30'

- interval: 24h
  name: capz-azure-file-${release/./-}
  decorate: true
  decoration_config:
    timeout: 3h
  labels:
    preset-dind-enabled: "true"
    preset-kind-volume-mounts: "true"
    preset-azure-cred: "true"
  extra_refs:
  - org: kubernetes-sigs
    repo: cluster-api-provider-azure
    base_ref: main
    path_alias: sigs.k8s.io/cluster-api-provider-azure
  - org: kubernetes-sigs
    repo: azurefile-csi-driver
    base_ref: master
    path_alias: sigs.k8s.io/azurefile-csi-driver
  - org: kubernetes
    repo: kubernetes
    base_ref: ${branch}
    path_alias: k8s.io/kubernetes
  spec:
    containers:
    - image: ${kubekins_e2e_image}-master
      command:
      - runner.sh
      - ./scripts/ci-entrypoint.sh
      args:
      - bash
      - -c
      - >-
        kubectl apply -f templates/addons/azurefile-role.yaml &&
        cd \${GOPATH}/src/sigs.k8s.io/azurefile-csi-driver &&
        make e2e-test
      env:
      - name: USE_CI_ARTIFACTS
        value: "true"
      - name: AZURE_STORAGE_DRIVER
        value: kubernetes.io/azure-file # In-tree Azure file storage class
      securityContext:
        privileged: true
      resources:
        requests:
          cpu: 1
          memory: "4Gi"
  annotations:
    testgrid-dashboards: provider-azure-${release}-signal
    testgrid-tab-name: capz-azure-file
    testgrid-alert-email: kubernetes-provider-azure@googlegroups.com
    testgrid-num-columns-recent: '30'

- interval: 24h
  name: capz-azure-file-vmss-${release/./-}
  decorate: true
  decoration_config:
    timeout: 3h
  labels:
    preset-dind-enabled: "true"
    preset-kind-volume-mounts: "true"
    preset-azure-cred: "true"
  extra_refs:
  - org: kubernetes-sigs
    repo: cluster-api-provider-azure
    base_ref: main
    path_alias: sigs.k8s.io/cluster-api-provider-azure
  - org: kubernetes-sigs
    repo: azurefile-csi-driver
    base_ref: master
    path_alias: sigs.k8s.io/azurefile-csi-driver
  - org: kubernetes
    repo: kubernetes
    base_ref: ${branch}
    path_alias: k8s.io/kubernetes
  spec:
    containers:
    - image: ${kubekins_e2e_image}-master
      command:
      - runner.sh
      - ./scripts/ci-entrypoint.sh
      args:
      - bash
      - -c
      - >-
        kubectl apply -f templates/addons/azurefile-role.yaml &&
        cd \${GOPATH}/src/sigs.k8s.io/azurefile-csi-driver &&
        make e2e-test
      env:
      - name: USE_CI_ARTIFACTS
        value: "true"
      - name: EXP_MACHINE_POOL
        value: "true"
      - name: AZURE_STORAGE_DRIVER
        value: kubernetes.io/azure-file # In-tree Azure file storage class
      securityContext:
        privileged: true
      resources:
        requests:
          cpu: 1
          memory: "4Gi"
  annotations:
    testgrid-dashboards: provider-azure-${release}-signal
    testgrid-tab-name: capz-azure-file-vmss
    testgrid-alert-email: kubernetes-provider-azure@googlegroups.com
    testgrid-num-columns-recent: '30'

- interval: 24h
  name: capz-azure-disk-${release/./-}
  decorate: true
  decoration_config:
    timeout: 3h
  labels:
    preset-dind-enabled: "true"
    preset-kind-volume-mounts: "true"
    preset-azure-cred: "true"
  extra_refs:
  - org: kubernetes-sigs
    repo: cluster-api-provider-azure
    base_ref: main
    path_alias: sigs.k8s.io/cluster-api-provider-azure
  - org: kubernetes-sigs
    repo: azuredisk-csi-driver
    base_ref: master
    path_alias: sigs.k8s.io/azuredisk-csi-driver
  - org: kubernetes
    repo: kubernetes
    base_ref: ${branch}
    path_alias: k8s.io/kubernetes
  spec:
    containers:
    - image: ${kubekins_e2e_image}-master
      command:
      - runner.sh
      - ./scripts/ci-entrypoint.sh
      args:
      - bash
      - -c
      - >-
        cd \${GOPATH}/src/sigs.k8s.io/azuredisk-csi-driver &&
        make e2e-test
      env:
      - name: USE_CI_ARTIFACTS
        value: "true"
      - name: AZURE_STORAGE_DRIVER
        value: kubernetes.io/azure-disk # In-tree Azure disk storage class
      securityContext:
        privileged: true
      resources:
        requests:
          cpu: 1
          memory: "4Gi"
  annotations:
    testgrid-dashboards: provider-azure-${release}-signal
    testgrid-tab-name: capz-azure-disk
    testgrid-alert-email: kubernetes-provider-azure@googlegroups.com
    testgrid-num-columns-recent: '30'

- interval: 24h
  name: capz-azure-disk-vmss-${release/./-}
  decorate: true
  decoration_config:
    timeout: 3h
  labels:
    preset-dind-enabled: "true"
    preset-kind-volume-mounts: "true"
    preset-azure-cred: "true"
  extra_refs:
  - org: kubernetes-sigs
    repo: cluster-api-provider-azure
    base_ref: main
    path_alias: sigs.k8s.io/cluster-api-provider-azure
  - org: kubernetes-sigs
    repo: azuredisk-csi-driver
    base_ref: master
    path_alias: sigs.k8s.io/azuredisk-csi-driver
  - org: kubernetes
    repo: kubernetes
    base_ref: ${branch}
    path_alias: k8s.io/kubernetes
  spec:
    containers:
    - image: ${kubekins_e2e_image}-master
      command:
      - runner.sh
      - ./scripts/ci-entrypoint.sh
      args:
      - bash
      - -c
      - >-
        cd \${GOPATH}/src/sigs.k8s.io/azuredisk-csi-driver &&
        make e2e-test
      env:
      - name: USE_CI_ARTIFACTS
        value: "true"
      - name: EXP_MACHINE_POOL
        value: "true"
      - name: AZURE_STORAGE_DRIVER
        value: kubernetes.io/azure-disk # In-tree Azure disk storage class
      securityContext:
        privileged: true
      resources:
        requests:
          cpu: 1
          memory: "4Gi"
  annotations:
    testgrid-dashboards: provider-azure-${release}-signal
    testgrid-tab-name: capz-azure-disk-vmss
    testgrid-alert-email: kubernetes-provider-azure@googlegroups.com
    testgrid-num-columns-recent: '30'
EOF
done
