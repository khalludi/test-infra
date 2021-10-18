# Copyright 2020 The Kubernetes Authors.
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

import hashlib
import math
import json
import re
import jinja2 # pylint: disable=import-error
import yaml


from helpers import ( # pylint: disable=import-error, no-name-in-module
    build_cron,
    create_args,
    distro_images,
    distros_ssh_user,
    k8s_version_info,
    should_skip_newer_k8s,
)

# These are job tab names of unsupported grid combinations
skip_jobs = [
]

image = "gcr.io/k8s-staging-test-infra/kubekins-e2e:v20211014-1439a9f025-master"

##############
# Build Test #
##############

# Returns a string representing the periodic prow job and the number of job invocations per week
def build_test(cloud='aws',
               distro='u2004',
               networking='kubenet',
               container_runtime='containerd',
               k8s_version='latest',
               kops_channel='alpha',
               kops_version=None,
               publish_version_marker=None,
               name_override=None,
               feature_flags=(),
               extra_flags=None,
               extra_dashboards=None,
               terraform_version=None,
               test_parallelism=25,
               test_timeout_minutes=60,
               skip_regex='',
               focus_regex=None,
               runs_per_day=0,
               scenario=None,
               env=None,
               template_path=None):
    # pylint: disable=too-many-statements,too-many-branches,too-many-arguments

    if kops_version is None:
        # TODO: Move to kops-ci/markers/master/ once validated
        kops_deploy_url = "https://storage.googleapis.com/kops-ci/bin/latest-ci-updown-green.txt"
    elif kops_version.startswith("https://"):
        kops_deploy_url = kops_version
        kops_version = None
    else:
        kops_deploy_url = f"https://storage.googleapis.com/kops-ci/markers/release-{kops_version}/latest-ci-updown-green.txt" # pylint: disable=line-too-long


    # https://github.com/cilium/cilium/blob/f7a3f59fd74983c600bfce9cac364b76d20849d9/Documentation/operations/system_requirements.rst
    if networking in ("cilium", "cilium-etcd") and distro not in ["u2004", "u2004arm64", "deb10", "rhel8", "amzn2"]: # pylint: disable=line-too-long
        return None
    if should_skip_newer_k8s(k8s_version, kops_version):
        return None

    if cloud == 'aws':
        kops_image = distro_images[distro]
        kops_ssh_user = distros_ssh_user[distro]
        kops_ssh_key_path = '/etc/aws-ssh/aws-ssh-private'

    elif cloud == 'gce':
        kops_image = None
        kops_ssh_user = 'prow'
        kops_ssh_key_path = '/etc/ssh-key-secret/ssh-private'

    validation_wait = '20m' if distro == 'flatcar' else None

    marker, k8s_deploy_url, test_package_bucket, test_package_dir = k8s_version_info(k8s_version)
    args = create_args(kops_channel, networking, container_runtime, extra_flags, kops_image)

    suffix = ""
    if cloud and cloud != "aws":
        suffix += "-" + cloud
    if networking and networking != "kubenet":
        suffix += "-" + networking
    if distro:
        suffix += "-" + distro
    if k8s_version:
        suffix += "-k" + k8s_version.replace("1.", "")
    if kops_version:
        suffix += "-ko" + kops_version.replace("1.", "")
    if container_runtime:
        suffix += "-" + container_runtime

    tab = name_override or (f"kops-grid{suffix}")

    if tab in skip_jobs:
        return None
    job_name = f"e2e-{tab}"

    cron, runs_per_week = build_cron(tab, runs_per_day)

    # Scenario-specific parameters
    if env is None:
        env = {}

    tmpl_file = "periodic.yaml.jinja"
    if scenario is not None:
        tmpl_file = "periodic-scenario.yaml.jinja"
        name_hash = hashlib.md5(job_name.encode()).hexdigest()
        env['CLOUD_PROVIDER'] = cloud
        env['CLUSTER_NAME'] = f"e2e-{name_hash[0:10]}-{name_hash[12:17]}.test-cncf-aws.k8s.io"
        env['KOPS_STATE_STORE'] = 's3://k8s-kops-prow'
        env['KUBE_SSH_USER'] = kops_ssh_user

    loader = jinja2.FileSystemLoader(searchpath="./templates")
    tmpl = jinja2.Environment(loader=loader).get_template(tmpl_file)
    job = tmpl.render(
        job_name=job_name,
        cloud=cloud,
        cron=cron,
        kops_ssh_user=kops_ssh_user,
        kops_ssh_key_path=kops_ssh_key_path,
        create_args=args,
        k8s_deploy_url=k8s_deploy_url,
        kops_deploy_url=kops_deploy_url,
        test_parallelism=str(test_parallelism),
        job_timeout=str(test_timeout_minutes + 30) + 'm',
        test_timeout=str(test_timeout_minutes) + 'm',
        marker=marker,
        template_path=template_path,
        skip_regex=skip_regex,
        kops_feature_flags=','.join(feature_flags),
        terraform_version=terraform_version,
        test_package_bucket=test_package_bucket,
        test_package_dir=test_package_dir,
        focus_regex=focus_regex,
        publish_version_marker=publish_version_marker,
        validation_wait=validation_wait,
        image=image,
        scenario=scenario,
        env=env,
    )

    spec = {
        'cloud': cloud,
        'networking': networking,
        'distro': distro,
        'k8s_version': k8s_version,
        'kops_version': kops_version,
        'container_runtime': container_runtime,
        'kops_channel': kops_channel,
    }
    if feature_flags:
        spec['feature_flags'] = ','.join(feature_flags)
    if extra_flags:
        spec['extra_flags'] = ' '.join(extra_flags)
    jsonspec = json.dumps(spec, sort_keys=True)

    dashboards = [
        'sig-cluster-lifecycle-kops',
        f"kops-distro-{distro}",
        f"kops-k8s-{k8s_version or 'latest'}",
        f"kops-{kops_version or 'latest'}",
    ]
    if cloud == 'aws':
        dashboards.extend(['google-aws'])
    if cloud == 'gce':
        dashboards.extend(['kops-gce'])

    if extra_dashboards:
        dashboards.extend(extra_dashboards)

    days_of_results = 90
    if runs_per_week * days_of_results > 2000:
        # testgrid has a limit on number of test runs to show for a job
        days_of_results = math.floor(2000 / runs_per_week)
    annotations = {
        'testgrid-dashboards': ', '.join(sorted(dashboards)),
        'testgrid-days-of-results': str(days_of_results),
        'testgrid-tab-name': tab,
    }
    for (k, v) in spec.items():
        annotations[f"test.kops.k8s.io/{k}"] = v or ""

    extra = yaml.dump({'annotations': annotations}, width=9999, default_flow_style=False)

    output = f"\n# {jsonspec}\n{job.strip()}\n"
    for line in extra.splitlines():
        output += f"  {line}\n"
    return output, runs_per_week

# Returns a string representing a presubmit prow job YAML
def presubmit_test(branch='master',
                   cloud='aws',
                   distro='u2004',
                   networking='kubenet',
                   container_runtime='containerd',
                   k8s_version='latest',
                   kops_channel='alpha',
                   name=None,
                   tab_name=None,
                   feature_flags=(),
                   extra_flags=None,
                   extra_dashboards=None,
                   test_parallelism=25,
                   test_timeout_minutes=60,
                   skip_regex='',
                   focus_regex=None,
                   run_if_changed=None,
                   skip_report=False,
                   always_run=False,
                   scenario=None,
                   env=None,
                   template_path=None):
    # pylint: disable=too-many-statements,too-many-branches,too-many-arguments
    if cloud == 'aws':
        kops_image = distro_images[distro]
        kops_ssh_user = distros_ssh_user[distro]
        kops_ssh_key_path = '/etc/aws-ssh/aws-ssh-private'

    elif cloud == 'gce':
        kops_image = None
        kops_ssh_user = 'prow'
        kops_ssh_key_path = '/etc/ssh-key-secret/ssh-private'

    marker, k8s_deploy_url, test_package_bucket, test_package_dir = k8s_version_info(k8s_version)
    args = create_args(kops_channel, networking, container_runtime, extra_flags, kops_image)

    # Scenario-specific parameters
    if env is None:
        env = {}

    tmpl_file = "presubmit.yaml.jinja"
    if scenario is not None:
        tmpl_file = "presubmit-scenario.yaml.jinja"
        name_hash = hashlib.md5(name.encode()).hexdigest()
        env['CLOUD_PROVIDER'] = cloud
        env['CLUSTER_NAME'] = f"e2e-{name_hash[0:10]}-{name_hash[11:16]}.test-cncf-aws.k8s.io"
        env['KOPS_STATE_STORE'] = 's3://k8s-kops-prow'

    loader = jinja2.FileSystemLoader(searchpath="./templates")
    tmpl = jinja2.Environment(loader=loader).get_template(tmpl_file)
    job = tmpl.render(
        job_name=name,
        branch=branch,
        cloud=cloud,
        kops_ssh_key_path=kops_ssh_key_path,
        kops_ssh_user=kops_ssh_user,
        create_args=args,
        k8s_deploy_url=k8s_deploy_url,
        test_parallelism=str(test_parallelism),
        job_timeout=str(test_timeout_minutes + 30) + 'm',
        test_timeout=str(test_timeout_minutes) + 'm',
        marker=marker,
        skip_regex=skip_regex,
        kops_feature_flags=','.join(feature_flags),
        test_package_bucket=test_package_bucket,
        test_package_dir=test_package_dir,
        focus_regex=focus_regex,
        run_if_changed=run_if_changed,
        skip_report='true' if skip_report else 'false',
        always_run='true' if always_run else 'false',
        image=image,
        scenario=scenario,
        env=env,
        template_path=template_path,
    )

    spec = {
        'cloud': cloud,
        'networking': networking,
        'distro': distro,
        'k8s_version': k8s_version,
        'container_runtime': container_runtime,
        'kops_channel': kops_channel,
    }
    if feature_flags:
        spec['feature_flags'] = ','.join(feature_flags)
    if extra_flags:
        spec['extra_flags'] = ' '.join(extra_flags)
    jsonspec = json.dumps(spec, sort_keys=True)

    dashboards = [
        'presubmits-kops',
        'kops-presubmits',
        'sig-cluster-lifecycle-kops',
        f"kops-distro-{distro}",
        f"kops-k8s-{k8s_version or 'latest'}",
    ]
    if extra_dashboards:
        dashboards.extend(extra_dashboards)

    annotations = {
        'testgrid-dashboards': ', '.join(sorted(dashboards)),
        'testgrid-days-of-results': '90',
        'testgrid-tab-name': tab_name or name,
    }
    for (k, v) in spec.items():
        annotations[f"test.kops.k8s.io/{k}"] = v or ""

    extra = yaml.dump({'annotations': annotations}, width=9999, default_flow_style=False)

    output = f"\n# {jsonspec}{job}\n"
    for line in extra.splitlines():
        output += f"    {line}\n"
    return output

####################
# Grid Definitions #
####################

networking_options = [
    'kubenet',
    'calico',
    'cilium',
    'cilium-etcd',
    'flannel',
    'kopeio',
]

distro_options = [
    'amzn2',
    'deb9',
    'deb10',
    'flatcar',
    'rhel7',
    'rhel8',
    'u1804',
    'u2004',
]

k8s_versions = [
    #"latest", # disabled until we're ready to test 1.23
    "1.20",
    "1.21",
    "1.22"
]

kops_versions = [
    None, # maps to latest
    "1.21",
    "1.22"
]

container_runtimes = [
    "docker",
    "containerd",
]

############################
# kops-periodics-grid.yaml #
############################
def generate_grid():
    results = []
    # pylint: disable=too-many-nested-blocks
    for container_runtime in container_runtimes:
        for networking in networking_options:
            for distro in distro_options:
                for k8s_version in k8s_versions:
                    for kops_version in kops_versions:
                        # https://github.com/kubernetes/kops/pull/11696
                        if kops_version is None and distro in ["deb9", "rhel7", "u1804"]:
                            continue
                        results.append(
                            build_test(cloud="aws",
                                       distro=distro,
                                       extra_dashboards=['kops-grid'],
                                       k8s_version=k8s_version,
                                       kops_version=kops_version,
                                       networking=networking,
                                       container_runtime=container_runtime)
                        )

    # Manually expand grid coverage for GCP
    # TODO(justinsb): merge into above block when we can
    # pylint: disable=too-many-nested-blocks
    for container_runtime in container_runtimes:
        for networking in ['kubenet', 'calico', 'cilium']: # TODO: all networking_options:
            for distro in ['u2004']: # TODO: all distro_options:
                for k8s_version in ["1.22"]: # TODO: all k8s_versions:
                    for kops_version in [None]: # TODO: all kops_versions:
                        # https://github.com/kubernetes/kops/pull/11696
                        if kops_version is None and distro in ["deb9", "rhel7", "u1804"]:
                            continue
                        results.append(
                            build_test(cloud="gce",
                                       distro=distro,
                                       extra_dashboards=['kops-grid'],
                                       k8s_version=k8s_version,
                                       kops_version=kops_version,
                                       networking=networking,
                                       container_runtime=container_runtime)
                        )

    return filter(None, results)

#############################
# kops-periodics-misc2.yaml #
#############################
def generate_misc():
    results = [
        # A one-off scenario testing arm64
        build_test(name_override="kops-grid-scenario-arm64",
                   cloud="aws",
                   distro="u2004arm64",
                   extra_flags=["--zones=eu-central-1a",
                                "--node-size=m6g.large",
                                "--master-size=m6g.large"],
                   extra_dashboards=['kops-misc']),

        # A special test for IPv6 Conformance
        build_test(name_override="kops-grid-scenario-ipv6-conformance",
                   cloud="aws",
                   distro="u2004",
                   k8s_version="ci",
                   networking="calico",
                   feature_flags=["AWSIPv6"],
                   runs_per_day=3,
                   extra_flags=['--ipv6',
                                '--api-loadbalancer-type=public',
                                '--api-loadbalancer-class=network',
                                '--zones=eu-west-1a',
                                '--set=cluster.spec.api.loadBalancer.useForInternalApi=true',
                                '--set=cluster.spec.cloudControllerManager.cloudProvider=aws',
                                '--set=cluster.spec.nonMasqueradeCIDR=fd00:10:96::/64',
                                ],
                   focus_regex=r'\[Conformance\]|\[NodeConformance\]',
                   extra_dashboards=['kops-misc', 'kops-ipv6']),
        # A special test for IPv6 using Calico CNI
        build_test(name_override="kops-grid-scenario-ipv6-calico",
                   cloud="aws",
                   distro="u2004",
                   k8s_version="ci",
                   networking="calico",
                   feature_flags=["AWSIPv6"],
                   runs_per_day=6,
                   extra_flags=['--ipv6',
                                '--api-loadbalancer-type=public',
                                '--api-loadbalancer-class=network',
                                '--zones=eu-west-1a',
                                '--set=cluster.spec.api.loadBalancer.useForInternalApi=true',
                                '--set=cluster.spec.cloudControllerManager.cloudProvider=aws',
                                '--set=cluster.spec.nonMasqueradeCIDR=fd00:10:96::/64',
                                ],
                   extra_dashboards=['kops-misc', 'kops-ipv6']),
        # A special test for IPv6 using Cilium CNI
        build_test(name_override="kops-grid-scenario-ipv6-cilium",
                   cloud="aws",
                   distro="u2004",
                   k8s_version="ci",
                   networking="cilium",
                   feature_flags=["AWSIPv6"],
                   runs_per_day=3,
                   extra_flags=['--ipv6',
                                '--api-loadbalancer-type=public',
                                '--api-loadbalancer-class=network',
                                '--zones=eu-west-1a',
                                '--set=cluster.spec.api.loadBalancer.useForInternalApi=true',
                                '--set=cluster.spec.cloudControllerManager.cloudProvider=aws',
                                '--set=cluster.spec.nonMasqueradeCIDR=fd00:10:96::/64',
                                ],
                   extra_dashboards=['kops-misc', 'kops-ipv6']),
        # A special test for IPv6 using Cilium CNI, kubeproxy and cloud IPAM
        build_test(name_override="kops-grid-scenario-ipv6-cilium-cloudipam",
                   cloud="aws",
                   distro="u2004",
                   k8s_version="ci",
                   networking="cilium",
                   feature_flags=["AWSIPv6"],
                   runs_per_day=3,
                   extra_flags=['--ipv6',
                                '--api-loadbalancer-type=public',
                                '--api-loadbalancer-class=network',
                                '--zones=eu-west-1a',
                                '--set=cluster.spec.api.loadBalancer.useForInternalApi=true',
                                '--set=cluster.spec.cloudControllerManager.cloudProvider=aws',
                                '--set=cluster.spec.nonMasqueradeCIDR=fd00:10:96::/64',
                                '--set=cluster.spec.podCIDRFromCloud=true',
                                ],
                   extra_dashboards=['kops-misc', 'kops-ipv6']),


        # A special test for JWKS
        build_test(name_override="kops-grid-scenario-service-account-iam",
                   cloud="aws",
                   distro="u2004",
                   runs_per_day=3,
                   extra_flags=['--api-loadbalancer-type=public',
                                '--override=cluster.spec.serviceAccountIssuerDiscovery.discoveryStore=s3://k8s-kops-prow/e2e-dc69f71486-5831d.test-cncf-aws.k8s.io/discovery', # pylint: disable=line-too-long
                                '--override=cluster.spec.serviceAccountIssuerDiscovery.enableAWSOIDCProvider=true', # pylint: disable=line-too-long
                                '--override=cluster.spec.iam.useServiceAccountExternalPermissions=true' # pylint: disable=line-too-long
                                ],
                   extra_dashboards=['kops-misc']),

        # A special test for warm pool
        build_test(name_override="kops-warm-pool",
                   runs_per_day=3,
                   networking="cilium",
                   extra_flags=['--api-loadbalancer-type=public',
                                '--override=cluster.spec.warmPool.minSize=1'
                                ],
                   extra_dashboards=['kops-misc']),

        # A special test for AWS Cloud-Controller-Manager
        build_test(name_override="kops-grid-scenario-aws-cloud-controller-manager",
                   cloud="aws",
                   distro="u2004",
                   k8s_version="ci",
                   runs_per_day=3,
                   extra_flags=['--override=cluster.spec.cloudControllerManager.cloudProvider=aws'],
                   extra_dashboards=['provider-aws-cloud-provider-aws', 'kops-misc']),

        # A special test for AWS Cloud-Controller-Manager and irsa
        build_test(name_override="kops-grid-scenario-aws-cloud-controller-manager-irsa",
                   cloud="aws",
                   distro="u2004",
                   k8s_version="ci",
                   runs_per_day=3,
                   extra_flags=['--override=cluster.spec.cloudControllerManager.cloudProvider=aws',
                                '--override=cluster.spec.serviceAccountIssuerDiscovery.discoveryStore=s3://k8s-kops-prow/kops-grid-scenario-aws-cloud-controller-manager-irsa/discovery', # pylint: disable=line-too-long
                                '--override=cluster.spec.serviceAccountIssuerDiscovery.enableAWSOIDCProvider=true', # pylint: disable=line-too-long
                                '--override=cluster.spec.iam.useServiceAccountExternalPermissions=true'], # pylint: disable=line-too-long

                   extra_dashboards=['provider-aws-cloud-provider-aws', 'kops-misc']),

        build_test(name_override="kops-grid-scenario-terraform",
                   k8s_version="1.20",
                   terraform_version="1.0.5",
                   extra_flags=["--zones=us-west-1a"],
                   extra_dashboards=['kops-misc']),

        build_test(name_override="kops-aws-misc-ha-euwest1",
                   k8s_version="stable",
                   networking="calico",
                   kops_channel="alpha",
                   runs_per_day=3,
                   extra_flags=["--master-count=3", "--zones=eu-west-1a,eu-west-1b,eu-west-1c"],
                   extra_dashboards=["kops-misc"]),

        build_test(name_override="kops-aws-misc-arm64-release",
                   k8s_version="ci",
                   distro="u2004arm64",
                   networking="calico",
                   kops_channel="alpha",
                   runs_per_day=3,
                   extra_flags=["--zones=eu-central-1a",
                                "--node-size=m6g.large",
                                "--master-size=m6g.large"],
                   extra_dashboards=["kops-misc"]),

        build_test(name_override="kops-aws-misc-arm64-ci",
                   k8s_version="ci",
                   distro="u2004arm64",
                   networking="calico",
                   kops_channel="alpha",
                   runs_per_day=3,
                   extra_flags=["--zones=eu-central-1a",
                                "--node-size=m6g.large",
                                "--master-size=m6g.large"],
                   extra_dashboards=["kops-misc"]),

        build_test(name_override="kops-aws-misc-arm64-conformance",
                   k8s_version="ci",
                   distro="u2004arm64",
                   networking="calico",
                   kops_channel="alpha",
                   runs_per_day=3,
                   extra_flags=["--zones=eu-central-1a",
                                "--node-size=m6g.large",
                                "--master-size=m6g.large"],
                   skip_regex=r'\[Slow\]|\[Serial\]|\[Flaky\]',
                   focus_regex=r'\[Conformance\]|\[NodeConformance\]',
                   extra_dashboards=["kops-misc"]),

        build_test(name_override="kops-aws-misc-amd64-conformance",
                   k8s_version="ci",
                   distro='u2004',
                   kops_channel="alpha",
                   runs_per_day=3,
                   extra_flags=["--node-size=c5.large",
                                "--master-size=c5.large"],
                   skip_regex=r'\[Slow\]|\[Serial\]|\[Flaky\]',
                   focus_regex=r'\[Conformance\]|\[NodeConformance\]',
                   extra_dashboards=["kops-misc"]),

        build_test(name_override="kops-aws-misc-updown",
                   k8s_version="stable",
                   networking="calico",
                   distro='u2004',
                   kops_channel="alpha",
                   kops_version="https://storage.googleapis.com/kops-ci/bin/latest-ci.txt",
                   publish_version_marker="gs://kops-ci/bin/latest-ci-updown-green.txt",
                   runs_per_day=24,
                   extra_flags=["--node-size=c5.large",
                                "--master-size=c5.large"],
                   focus_regex=r'\[k8s.io\]\sNetworking.*\[Conformance\]',
                   extra_dashboards=["kops-misc"]),

        build_test(name_override="kops-grid-scenario-cilium10-arm64",
                   cloud="aws",
                   networking="cilium",
                   distro="u2004arm64",
                   kops_channel="alpha",
                   runs_per_day=1,
                   extra_flags=["--zones=eu-central-1a",
                                "--node-size=m6g.large",
                                "--master-size=m6g.large"],
                   extra_dashboards=['kops-misc']),

        build_test(name_override="kops-grid-scenario-cilium10-amd64",
                   cloud="aws",
                   networking="cilium",
                   distro="u2004",
                   kops_channel="alpha",
                   runs_per_day=1,
                   extra_flags=["--zones=eu-central-1a",
                                "--override=cluster.spec.networking.cilium.version=v1.10.0-rc2"],
                   extra_dashboards=['kops-misc']),

        build_test(name_override="kops-aws-aws-ebs-csi-driver",
                   cloud="aws",
                   networking="cilium",
                   distro="u2004",
                   kops_channel="alpha",
                   runs_per_day=3,
                   scenario="aws-ebs-csi",
                   extra_dashboards=['kops-misc']),

        build_test(name_override="kops-aws-aws-ebs-csi-driver-irsa",
                   cloud="aws",
                   networking="cilium",
                   distro="u2004",
                   kops_channel="alpha",
                   runs_per_day=3,
                   scenario="aws-ebs-csi",
                   env={'KOPS_IRSA': 'true'},
                   extra_flags=["--override=cluster.spec.iam.useServiceAccountExternalPermissions=true"], # pylint: disable=line-too-long
                   extra_dashboards=['kops-misc']),

        build_test(name_override="kops-aws-aws-load-balancer-controller",
                   cloud="aws",
                   networking="cilium",
                   distro="u2004",
                   k8s_version='1.21', # TODO(rifelpet): remove when kops#11689 is addressed
                   kops_channel="alpha",
                   runs_per_day=1,
                   scenario="aws-lb-controller",
                   extra_dashboards=['kops-misc']),

        build_test(name_override="kops-aws-aws-load-balancer-controller-irsa",
                   cloud="aws",
                   networking="cilium",
                   distro="u2004",
                   k8s_version='1.21', # TODO(rifelpet): remove when kops#11689 is addressed
                   kops_channel="alpha",
                   runs_per_day=3,
                   scenario="aws-lb-controller",
                   env={'KOPS_IRSA': 'true'},
                   extra_dashboards=['kops-misc']),

        build_test(name_override="kops-aws-keypair-rotation",
                   cloud="aws",
                   kops_channel="alpha",
                   runs_per_day=1,
                   test_timeout_minutes=120,
                   scenario="keypair-rotation",
                   extra_dashboards=['kops-misc']),

        build_test(name_override="kops-aws-metrics-server",
                   cloud="aws",
                   networking="cilium",
                   distro="u2004",
                   kops_channel="alpha",
                   runs_per_day=3,
                   scenario="metrics-server",
                   extra_dashboards=['kops-misc']),

        build_test(name_override="kops-aws-external-dns",
                   cloud="aws",
                   networking="cilium",
                   distro="u2004",
                   kops_channel="alpha",
                   runs_per_day=3,
                   extra_flags=[
                       "--override=cluster.spec.externalDns.provider=external-dns"
                   ],
                   extra_dashboards=['kops-misc']),

        build_test(name_override="kops-aws-external-dns-irsa",
                   cloud="aws",
                   networking="cilium",
                   distro="u2004",
                   kops_channel="alpha",
                   runs_per_day=3,
                   extra_flags=[
                       "--override=cluster.spec.externalDns.provider=external-dns",
                       "--override=cluster.spec.iam.useServiceAccountExternalPermissions=true"
                   ],
                   extra_dashboards=['kops-misc']),

        build_test(name_override="kops-aws-apiserver-nodes",
                   cloud="aws",
                   runs_per_day=3,
                   template_path="/home/prow/go/src/k8s.io/kops/tests/e2e/templates/apiserver.yaml.tmpl", # pylint: disable=line-too-long
                   extra_dashboards=['kops-misc'],
                   feature_flags=['APIServerNodes']),

    ]
    return results

###############################
# kops-periodics-distros.yaml #
###############################
def generate_distros():
    distros = ['debian9', 'debian10', 'debian11', 'ubuntu1804', 'ubuntu2004', 'ubuntu2104',
               'centos7', 'centos8', 'amazonlinux2', 'rhel7', 'rhel8', 'flatcar']
    results = []
    for distro in distros:
        distro_short = distro.replace('ubuntu', 'u').replace('debian', 'deb').replace('amazonlinux', 'amzn') # pylint: disable=line-too-long
        results.append(
            build_test(distro=distro_short,
                       networking='calico',
                       k8s_version='stable',
                       kops_channel='alpha',
                       name_override=f"kops-aws-distro-image{distro}",
                       extra_dashboards=['kops-distros'],
                       runs_per_day=3,
                       )
        )
    return results

#######################################
# kops-periodics-network-plugins.yaml #
#######################################
def generate_network_plugins():

    plugins = ['amazon-vpc', 'calico', 'canal', 'cilium', 'cilium-etcd', 'flannel', 'kopeio', 'kuberouter', 'weave'] # pylint: disable=line-too-long
    plugins_121 = ['amazon-vpc', 'canal'] # TODO(rifelpet): remove when kops#11689 is addressed
    results = []
    for plugin in plugins:
        networking_arg = plugin.replace('amazon-vpc', 'amazonvpc').replace('kuberouter', 'kube-router') # pylint: disable=line-too-long
        results.append(
            build_test(
                k8s_version='1.21' if plugin in plugins_121 else 'stable',
                kops_channel='alpha',
                name_override=f"kops-aws-cni-{plugin}",
                networking=networking_arg,
                extra_flags=['--node-size=t3.large'],
                extra_dashboards=['kops-network-plugins'],
                runs_per_day=3,
            )
        )
    return results

################################
# kops-periodics-upgrades.yaml #
################################
def generate_upgrades():
    versions_list = [
        #  kops    k8s          kops      k8s
        (('1.21', 'v1.21.0'), ('latest', 'latest')),
        (('1.22', 'v1.22.0'), ('latest', 'latest')),
        (('1.21', 'v1.21.0'), ('1.22', 'v1.22.0')),
        (('1.20', 'v1.20.7'), ('1.21', 'v1.21.0')),
        (('latest', 'v1.20.6'), ('latest', 'v1.21.0')),
        (('latest', 'v1.18.6'), ('latest', 'v1.19.0')),
        (('1.20', 'v1.20.6'), ('latest', 'v1.21.0')),
    ]
    def shorten(version):
        version = re.sub(r'^v', '', version)
        version = re.sub(r'^(\d+\.\d+)\.\d+$', r'\g<1>', version)
        return version.replace('.', '')
    results = []
    for versions in versions_list:
        kops_a = versions[0][0]
        k8s_a = versions[0][1]
        kops_b = versions[1][0]
        k8s_b = versions[1][1]
        job_name = f"kops-aws-upgrade-k{shorten(k8s_a)}-ko{shorten(kops_a)}-to-k{shorten(k8s_b)}-ko{shorten(kops_b)}" # pylint: disable=line-too-long
        env = {
            'KOPS_VERSION_A': kops_a,
            'K8S_VERSION_A': k8s_a,
            'KOPS_VERSION_B': kops_b,
            'K8S_VERSION_B': k8s_b,
        }
        results.append(
            build_test(name_override=job_name,
                       distro='u2004',
                       networking='calico',
                       k8s_version='stable',
                       kops_channel='alpha',
                       extra_dashboards=['kops-misc'],
                       runs_per_day=12,
                       scenario='upgrade-ab',
                       env=env,
                       )
        )
    return results

################################
# kops-periodics-versions.yaml #
################################
def generate_versions():
    results = [
        build_test(
            k8s_version='ci',
            kops_channel='alpha',
            name_override='kops-aws-k8s-latest',
            networking='calico',
            extra_dashboards=['kops-versions'],
            runs_per_day=8,
            # This version marker is only used by the k/k presubmit job
            publish_version_marker='gs://kops-ci/bin/latest-ci-green.txt',
        )
    ]
    for version in ['1.22', '1.21', '1.20', '1.19', '1.18']:
        distro = 'deb9' if version == '1.17' else 'u2004'
        results.append(
            build_test(
                distro=distro,
                k8s_version=version,
                kops_channel='alpha',
                name_override=f"kops-aws-k8s-{version.replace('.', '-')}",
                networking='calico',
                extra_dashboards=['kops-versions'],
                runs_per_day=8,
            )
        )
    return results

######################
# kops-pipeline.yaml #
######################
def generate_pipeline():
    results = []
    for version in ['master', '1.22', '1.21', '1.20']:
        branch = version if version == 'master' else f"release-{version}"
        publish_version_marker = f"gs://kops-ci/markers/{branch}/latest-ci-updown-green.txt"
        kops_version = f"https://storage.googleapis.com/k8s-staging-kops/kops/releases/markers/{branch}/latest-ci.txt" # pylint: disable=line-too-long
        results.append(
            build_test(
                k8s_version=version.replace('master', 'latest'),
                kops_version=kops_version,
                kops_channel='alpha',
                name_override=f"kops-pipeline-updown-kops{version.replace('.', '')}",
                networking='calico',
                extra_dashboards=['kops-versions'],
                runs_per_day=24,
                skip_regex=r'\[Slow\]|\[Serial\]',
                focus_regex=r'\[k8s.io\]\sNetworking.*\[Conformance\]',
                publish_version_marker=publish_version_marker,
            )
        )
    return results

########################################
# kops-presubmits-network-plugins.yaml #
########################################
def generate_presubmits_network_plugins():
    plugins = {
        'amazonvpc': r'^(upup\/models\/cloudup\/resources\/addons\/networking\.amazon-vpc-routed-eni\/|pkg\/model\/(firewall|components\/kubeproxy|iam\/iam_builder).go|nodeup\/pkg\/model\/(context|kubelet).go|upup\/pkg\/fi\/cloudup\/defaults.go)', # pylint: disable=line-too-long
        'calico': r'^(upup\/models\/cloudup\/resources\/addons\/networking\.projectcalico\.org\/|pkg\/model\/(firewall.go|pki.go|iam\/iam_builder.go)|nodeup\/pkg\/model\/networking\/calico.go)', # pylint: disable=line-too-long
        'canal': r'^(upup\/models\/cloudup\/resources\/addons\/networking\.projectcalico\.org\.canal\/)', # pylint: disable=line-too-long
        'cilium': r'^(upup\/models\/cloudup\/resources\/addons\/networking\.cilium\.io\/|pkg\/model\/(firewall|components\/cilium|iam\/iam_builder).go|nodeup\/pkg\/model\/(context|networking\/cilium).go|upup\/pkg\/fi\/cloudup\/template_functions.go)', # pylint: disable=line-too-long
        'cilium-etcd': None,
        'flannel': r'^(upup\/models\/cloudup\/resources\/addons\/networking\.flannel\/|upup\/pkg\/fi\/cloudup\/template_functions.go)', # pylint: disable=line-too-long
        'kuberouter': r'^(upup\/models\/cloudup\/resources\/addons\/networking\.kuberouter\/|upup\/pkg\/fi\/cloudup\/template_functions.go)', # pylint: disable=line-too-long
        'weave': r'^(upup\/models\/cloudup\/resources\/addons\/networking\.weave\/|upup\/pkg\/fi\/cloudup\/template_functions.go)' # pylint: disable=line-too-long
    }
    plugins_121 = ['amazonvpc', 'canal'] # TODO(rifelpet): remove when kops#11689 is addressed
    results = []
    for plugin, run_if_changed in plugins.items():
        networking_arg = plugin
        if plugin == 'kuberouter':
            networking_arg = 'kube-router'
        results.append(
            presubmit_test(
                k8s_version='1.21' if plugin in plugins_121 else 'stable',
                kops_channel='alpha',
                name=f"pull-kops-e2e-cni-{plugin}",
                tab_name=f"e2e-{plugin}",
                networking=networking_arg,
                extra_flags=['--node-size=t3.large'],
                extra_dashboards=['kops-network-plugins'],
                run_if_changed=run_if_changed,
                skip_report=False,
                always_run=False,
            )
        )
    return results

############################
# kops-presubmits-e2e.yaml #
############################
def generate_presubmits_e2e():
    skip_regex = r'\[Slow\]|\[Serial\]|\[Disruptive\]|\[Flaky\]|\[Feature:.+\]|\[HPA\]|\[Driver:.nfs\]|Dashboard|RuntimeClass|RuntimeHandler' # pylint: disable=line-too-long
    jobs = [
        presubmit_test(
            k8s_version='ci',
            kops_channel='alpha',
            name='pull-kops-e2e-k8s-ci',
            networking='calico',
            tab_name='e2e-containerd-ci',
            always_run=False,
            focus_regex=r'\[Conformance\]|\[NodeConformance\]',
        ),
        presubmit_test(
            k8s_version='ci',
            kops_channel='alpha',
            name='pull-kops-e2e-k8s-ci-ha',
            networking='calico',
            extra_flags=[
                "--master-count=3",
                "--node-count=6",
                "--zones=eu-central-1a,eu-central-1b,eu-central-1c"],
            tab_name='e2e-containerd-ci-ha',
            always_run=False,
            focus_regex=r'\[Conformance\]|\[NodeConformance\]',
        ),
        presubmit_test(
            container_runtime='docker',
            k8s_version='1.21',
            kops_channel='alpha',
            name='pull-kops-e2e-k8s-docker',
            tab_name='e2e-docker',
            always_run=False,
        ),
        presubmit_test(
            k8s_version='1.21',
            kops_channel='alpha',
            name='pull-kops-e2e-kubernetes-aws',
            networking='calico',
            tab_name='e2e-containerd',
            always_run=True,
        ),
        presubmit_test(
            distro="u2010",
            networking='calico',
            k8s_version='1.21',
            kops_channel='alpha',
            name='pull-kops-e2e-k8s-ubuntu2010',
            tab_name='e2e-ubuntu2010',
            always_run=False,
        ),
        presubmit_test(
            distro="u2104",
            networking='calico',
            k8s_version='1.21',
            kops_channel='alpha',
            name='pull-kops-e2e-k8s-ubuntu2104',
            tab_name='e2e-ubuntu2104',
            always_run=False,
        ),
        presubmit_test(
            distro="deb11",
            networking='calico',
            k8s_version='1.21',
            kops_channel='alpha',
            name='pull-kops-e2e-k8s-debian11',
            tab_name='e2e-debian11',
            always_run=False,
        ),
        presubmit_test(
            cloud='gce',
            k8s_version='1.21',
            kops_channel='alpha',
            name='pull-kops-e2e-k8s-gce',
            networking='cilium',
            tab_name='e2e-gce',
            always_run=False,
            skip_regex=r'\[Slow\]|\[Serial\]|\[Disruptive\]|\[Flaky\]|\[Feature:.+\]|\[HPA\]|\[Driver:.nfs\]|Firewall|Dashboard|RuntimeClass|RuntimeHandler|kube-dns|run.a.Pod.requesting.a.RuntimeClass|should.set.TCP.CLOSE_WAIT|Services.*rejected.*endpoints', # pylint: disable=line-too-long
        ),
        # A special test for AWS Cloud-Controller-Manager
        presubmit_test(
            name="pull-kops-e2e-aws-cloud-controller-manager",
            cloud="aws",
            distro="u2004",
            k8s_version="ci",
            extra_flags=['--override=cluster.spec.cloudControllerManager.cloudProvider=aws'],
            tab_name='e2e-ccm',
        ),

        # A special test for AWS Cloud-Controller-Manager and irsa
        presubmit_test(
            name="pull-kops-e2e-aws-cloud-controller-manager-irsa",
            cloud="aws",
            distro="u2004",
            k8s_version="ci",
            extra_flags=[
                '--override=cluster.spec.iam.useServiceAccountExternalPermissions=true',
                '--override=cluster.spec.cloudControllerManager.cloudProvider=aws',
                '--override=cluster.spec.serviceAccountIssuerDiscovery.discoveryStore=s3://k8s-kops-prow/kops-grid-scenario-aws-cloud-controller-manager-irsa/discovery', # pylint: disable=line-too-long
                '--override=cluster.spec.serviceAccountIssuerDiscovery.enableAWSOIDCProvider=true'], # pylint: disable=line-too-long
            tab_name='e2e-ccm-irsa',
        ),

        presubmit_test(
            name="pull-kops-e2e-aws-irsa",
            cloud="aws",
            distro="u2004",
            k8s_version="ci",
            extra_flags=[
                '--override=cluster.spec.iam.useServiceAccountExternalPermissions=true',
                '--override=cluster.spec.serviceAccountIssuerDiscovery.discoveryStore=s3://k8s-kops-prow/pull-aws-irsa/discovery', # pylint: disable=line-too-long
                '--override=cluster.spec.serviceAccountIssuerDiscovery.enableAWSOIDCProvider=true'], # pylint: disable=line-too-long
        ),


        presubmit_test(
            name="pull-kops-e2e-ipv6-calico",
            cloud="aws",
            distro="u2004",
            k8s_version="ci",
            networking="calico",
            feature_flags=["AWSIPv6"],
            extra_flags=['--ipv6',
                         '--api-loadbalancer-type=public',
                         '--api-loadbalancer-class=network',
                         '--zones=eu-west-1a',
                         '--set=cluster.spec.api.loadBalancer.useForInternalApi=true',
                         '--set=cluster.spec.cloudControllerManager.cloudProvider=aws',
                         '--set=cluster.spec.nonMasqueradeCIDR=fd00:10:96::/64',
                         ],
            extra_dashboards=['kops-ipv6'],
        ),

        presubmit_test(
            name="pull-kops-e2e-ipv6-conformance",
            cloud="aws",
            distro="u2004",
            k8s_version="ci",
            networking="calico",
            feature_flags=["AWSIPv6"],
            extra_flags=['--ipv6',
                         '--api-loadbalancer-type=public',
                         '--api-loadbalancer-class=network',
                         '--zones=eu-west-1a',
                         '--set=cluster.spec.api.loadBalancer.useForInternalApi=true',
                         '--set=cluster.spec.cloudControllerManager.cloudProvider=aws',
                         '--set=cluster.spec.nonMasqueradeCIDR=fd00:10:96::/64',
                         ],
            focus_regex=r'\[Conformance\]|\[NodeConformance\]',
            extra_dashboards=['kops-ipv6'],
        ),

        presubmit_test(
            name="pull-kops-e2e-ipv6-cilium",
            cloud="aws",
            distro="u2004",
            k8s_version="ci",
            networking="cilium",
            feature_flags=["AWSIPv6"],
            extra_flags=['--ipv6',
                         '--api-loadbalancer-type=public',
                         '--api-loadbalancer-class=network',
                         '--zones=eu-west-1a',
                         '--set=cluster.spec.api.loadBalancer.useForInternalApi=true',
                         '--set=cluster.spec.cloudControllerManager.cloudProvider=aws',
                         '--set=cluster.spec.nonMasqueradeCIDR=fd00:10:96::/64',
                         ],
            extra_dashboards=['kops-ipv6'],
        ),

        presubmit_test(
            name="pull-kops-e2e-aws-ebs-csi-driver",
            cloud="aws",
            distro="u2004",
            k8s_version="ci",
            networking="calico",
            scenario="aws-ebs-csi",
        ),

        presubmit_test(
            name="pull-kops-e2e-aws-ebs-csi-driver-irsa",
            cloud="aws",
            distro="u2004",
            k8s_version="ci",
            networking="calico",
            extra_flags=['--override=cluster.spec.iam.useServiceAccountExternalPermissions=true'], # pylint: disable=line-too-long
            scenario="aws-ebs-csi",
        ),

        presubmit_test(
            name="pull-e2e-kops-aws-load-balancer-controller",
            cloud="aws",
            distro="u2004",
            k8s_version="ci",
            networking="calico",
            scenario="aws-lb-controller",
            tab_name="pull-kops-e2e-aws-load-balancer-controller",
        ),

        presubmit_test(
            name="pull-e2e-kops-addon-resource-tracking",
            cloud="aws",
            distro="u2004",
            k8s_version="ci",
            networking="calico",
            scenario="addon-resource-tracking",
            tab_name="pull-kops-e2e-aws-addon-resource-tracking",
        ),

        presubmit_test(
            name="pull-e2e-kops-metrics-server",
            cloud="aws",
            distro="u2004",
            k8s_version="ci",
            networking="calico",
            scenario="metrics-server",
            tab_name="pull-kops-e2e-aws-metrics-server",
        ),

        presubmit_test(
            name="pull-kops-e2e-aws-external-dns",
            cloud="aws",
            distro="u2004",
            k8s_version="ci",
            networking="calico",
            extra_flags=[
                '--override=cluster.spec.externalDns.provider=external-dns'
            ],
        ),

        presubmit_test(
            name="pull-kops-e2e-aws-external-dns-irsa",
            cloud="aws",
            distro="u2004",
            k8s_version="ci",
            networking="calico",
            extra_flags=[
                '--override=cluster.spec.externalDns.provider=external-dns',
                '--override=cluster.spec.iam.useServiceAccountExternalPermissions=true'
            ],
        ),
        presubmit_test(
            name="pull-kops-e2e-aws-apiserver-nodes",
            cloud="aws",
            template_path="/home/prow/go/src/k8s.io/kops/tests/e2e/templates/apiserver.yaml.tmpl",
            feature_flags=['APIServerNodes']
        ),



    ]
    for branch in ['1.22', '1.21']:
        name_suffix = branch.replace('.', '-')
        jobs.append(
            presubmit_test(
                branch='release-' + branch,
                k8s_version=branch,
                kops_channel='alpha',
                name='pull-kops-e2e-kubernetes-aws-' + name_suffix,
                networking='calico',
                tab_name='e2e-' + name_suffix,
                always_run=True,
                skip_regex=skip_regex,
            )
        )
    return jobs

########################
# YAML File Generation #
########################
periodics_files = {
    'kops-periodics-distros.yaml': generate_distros,
    'kops-periodics-grid.yaml': generate_grid,
    'kops-periodics-misc2.yaml': generate_misc,
    'kops-periodics-network-plugins.yaml': generate_network_plugins,
    'kops-periodics-upgrades.yaml': generate_upgrades,
    'kops-periodics-versions.yaml': generate_versions,
    'kops-periodics-pipeline.yaml': generate_pipeline,
}

presubmits_files = {
    'kops-presubmits-network-plugins.yaml': generate_presubmits_network_plugins,
    'kops-presubmits-e2e.yaml': generate_presubmits_e2e,
}

def main():
    for filename, generate_func in periodics_files.items():
        print(f"Generating {filename}")
        output = []
        runs_per_week = 0
        job_count = 0
        for res in generate_func():
            output.append(res[0])
            runs_per_week += res[1]
            job_count += 1
        output.insert(0, "# Test jobs generated by build_jobs.py (do not manually edit)\n")
        output.insert(1, f"# {job_count} jobs, total of {runs_per_week} runs per week\n")
        output.insert(2, "periodics:\n")
        with open(filename, 'w') as fd:
            fd.write(''.join(output))
    for filename, generate_func in presubmits_files.items():
        print(f"Generating {filename}")
        output = []
        job_count = 0
        for res in generate_func():
            output.append(res)
            job_count += 1
        output.insert(0, "# Test jobs generated by build_jobs.py (do not manually edit)\n")
        output.insert(1, f"# {job_count} jobs\n")
        output.insert(2, "presubmits:\n")
        output.insert(3, "  kubernetes/kops:\n")
        with open(filename, 'w') as fd:
            fd.write(''.join(output))

if __name__ == "__main__":
    main()
