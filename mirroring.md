# Mirroring images with a bastion host

Last Updated: 2026-01-

If your OpenShift cluster is not connected to the internet, you can mirror images to a registry in your network-restricted environment by using a
bastion host. This task must be performed by a Red Hat OpenShift administrator.
A bastion host is a device that has access to both the public internet and the network-restricted environment where a local registry and Red Hat
OpenShift Container Platform clusters reside. Using the bastion host, you can mirror your images directly to the local registry.
The process for mirroring images involves the following steps:

1. Set up your mirroring environment
2. Set environment variables and download operator package files
3. Mirror the images

## 1. Set up your mirroring environment

Before you install any IBM Cloud Pak® on an air-gapped environment, you must set up a host that can be connected to the internet to complete
configuring your mirroring environment. To set up your mirroring environment, complete the following steps:

## 1.1 Prerequisites

```
Note:
This is the latest SC-2 (long term support) version of Cloud Pak for Integration. For the latest CD release, see What's new in Cloud Pak for
Integration 16.1.2.
```
```
Troubleshooting: For a list of possible errors and solutions, see Troubleshooting issues when mirroring images for an air-gapped
OpenShift cluster.
```
- 1.1 Prerequisites
- 1.2 Prepare a host
- 1.3 Set up local image registry and access

```
A Docker V2 registry that is available and accessible from the OpenShift Container Platform cluster nodes and the bastion host.
Ensure that you have sufficient registry space for all the operator packages that you intend to export. For more information, see "Sizing for
operator packages" in Mirroring images for an air-gapped OpenShift cluster.
```
##### –

- The following sites and ports must be accessible from the bastion host:
    ▪ icr.io:443 for open images
    ▪ cp.icr.io:443 for entitled registry images
    ▪ dd0.icr.io CDN for image content delivery
    ▪ dd2.icr.io CDN for image content delivery
    ▪ github.com for operator packages and tools
    ▪ redhat.com for Red Hat OpenShift Container Platform upgrades
- Storage is available and configured on your OpenShift cluster.


**Tip**
With ibm-pak plug-in version 1.2.0, you can eliminate the port for github.com to retrieve operator packages by configuring the plug-in to
download CASEs as OCI artifacts from IBM Cloud Container Registry (ICCR). Run this command:

### 1.2 Prepare a host for mirroring the images

You must be able to connect your bastion host to the internet and to the restricted network environment (with access to the OpenShift Container
Platform cluster and the local registry) at the same time. Your host must be on a Linux® x86_64 or Mac platform with any operating system that
the OpenShift Container Platform CLI supports.

The following table provides the software requirements for installing Cloud Pak for Integration in an air-gapped environment:

#### Software requirements and purpose

Complete the following steps on your host:

1. Install Docker or Podman.
2. Install the ocOpenShift Container Platform CLI tool.
    Follow the procedure for Getting started with the OpenShift CLI.
3. Download the IBM Catalog Management plug-in version 1.18.0 or later from GitHub. This plug-in allows you to run oc ibm-pak commands
    against your OpenShift cluster.
    To confirm that ibm-pak is installed, run the following command:

```
If you need to mirror the OpenShift operators, complete the following Prerequisites for mirroring images for a disconnected installation using
the oc-mirror plugin as described in the Red Hat OpenShift documentation.
For more information about why you might need these operators, see 3.8. Mirror Red Hat operators.
```
##### –

```
oc ibm-pak config repo 'IBM Cloud-Pak OCI registry' -r oci:cp.icr.io/cpopen --enable
```
```
Important: If you are on a Windows platform, you must execute the actions in a Linux x86_64 VM or from a Windows Subsystem for
Linux (WSL) terminal.
```
```
Software Purpose
Docker Container management
Podman Container management
oc Red Hat OpenShift Container Platform administration
oc ibm-pak oc IBM Catalog Management Plug-in for IBM Cloud Paks
```
```
▪ To install Docker (for example, on Red Hat® Enterprise Linux®), run the following commands:
```
```
yum check-updateyum install docker
```
```
▪ To install Podman, see Podman installation instructions.
```

```
This should return the oc ibm-pak usage.
```
### 1.3. Set up local image registry and access

Use a local Docker registry to store images in your network restricted environment. If you already have one or more centralized, corporate registry
servers that store production container images, you can use those for this purpose. If a registry is not already available, install and configure a
production-grade registry.

User access: To access your registries during the mirroring process, you need user credentials that can write to the target local registry and create
repositories. To access your registries during runtime, you need user credentials that can read all repositories from the target local registry (these
credentials are used by the OpenShift Container Platform cluster).
The local registry must meet the following requirements:

## 2. Set environment variables and download operator package files

Before mirroring your images, you need to set the environment variables on your mirroring device. You also need to connect to the internet, so
that you can download the corresponding operator package files. To finish preparing your host, complete the following steps.

### Before you begin

These prerequisites apply only if you are applying fix packs prior to an upgrade:

### Procedure

1. For each component of Cloud Pak for Integration that you intend to use, create environment variables with the installer image name and the
    image inventory on your host. Copy and run the applicable command in Export commands for operators.
    For example:

```
oc ibm-pak --help
```
```
Important: Do not use the OpenShift image registry as your local registry. The OpenShift registry does not support multi-architecture
images in the image name.
```
- Supports multi-architecture images through Docker Manifest V2, Schema 2. For details, see Docker Manifest V2, Schema 2
- Open Container Initiative (OCI) compliant.
- Has sufficient storage to hold all the software
- Is accessible from the OpenShift Container Platform cluster nodes
- Supports auto-repository creation
- Confirm that your operators are running properly.
    If there are any pending operator updates that require manual approval, approve those before starting this procedure. Manual approval should
    not be configured for operator installs, because users cannot control what upgrades to apply; this strategy forces all possible upgrades to be
    done at the same time and can block upgrades.

##### –


2. Connect your host to the internet. It does not need to be connected to the network-restricted environment at this time.
3. Download the operator package to your host. If you do not specify the operator version, it downloads the latest version.

Repeat the process for each operator package you are mirroring.
Your host is now configured and you are ready to mirror your images.

### Export commands for operators

Copy and run the applicable commands to set the environment variables for each operator that you need. For entries with an asterisk ("*"), make
sure to review the "Notes" section at the end of the list.

```
export OPERATOR_PACKAGE_NAME=ibm-integration-platform-navigator && export OPERATOR_VERSION=7.3.
```
```
oc ibm-pak get $OPERATOR_PACKAGE_NAME --version $OPERATOR_VERSION --skip-dependencies --install-method OLM
```
- IBM Cloud Pak for Integration

```
export OPERATOR_PACKAGE_NAME=ibm-integration-platform-navigator && export OPERATOR_VERSION=7.3.
```
- IBM Automation foundation assets

```
export OPERATOR_PACKAGE_NAME=ibm-integration-asset-repository && export OPERATOR_VERSION=1.7.
```
- IBM API Connect *****

```
export OPERATOR_PACKAGE_NAME=ibm-apiconnect && export OPERATOR_VERSION=5.7.
```
- IBM App Connect

```
export OPERATOR_PACKAGE_NAME=ibm-appconnect && export OPERATOR_VERSION=12.0.
```
- IBM MQ

```
export OPERATOR_PACKAGE_NAME=ibm-mq && export OPERATOR_VERSION=3.2.
```
- IBM Event Streams

```
export OPERATOR_PACKAGE_NAME=ibm-eventstreams && export OPERATOR_VERSION=12.2.
```
- IBM Event Endpoint Management

```
export OPERATOR_PACKAGE_NAME=ibm-eventendpointmanagement && export OPERATOR_VERSION=11.7.
```
- IBM Event Processing


**Notes**

## 3. Mirror the images

The process of mirroring images pulls the image from the internet and pushes it to your local registry. After mirroring the images, you can
configure your OpenShift cluster and complete the air-gapped installation.
Complete the following steps to mirror the images from your host to your air-gapped environment:

### 3.1. Generate mirror manifests

```
export OPERATOR_PACKAGE_NAME=ibm-eventprocessing && export OPERATOR_VERSION=1.4.
```
- IBM Operator for Apache Flink

```
export OPERATOR_PACKAGE_NAME=ibm-eventautomation-flink && export OPERATOR_VERSION=1.4.
```
- IBM DataPower Gateway ******

```
export OPERATOR_PACKAGE_NAME=ibm-datapower-operator && export OPERATOR_VERSION=1.11.
```
- IBM Aspera HSTS

```
export OPERATOR_PACKAGE_NAME=ibm-aspera-hsts-operator && export OPERATOR_VERSION=1.5.
```
- IBM Cloud Pak foundational services

```
export OPERATOR_PACKAGE_NAME=ibm-cp-common-services && export OPERATOR_VERSION=4.6.
```
- EDB Postgres for Kubernetes

```
export OPERATOR_PACKAGE_NAME=ibm-cloud-native-postgresql && export OPERATOR_VERSION=6.2.
```
```
* If you are planning to deploy the API Manager instance type, you need to mirror the EDB Postgres for Kubernetes operator package as well
as the IBM API Connect operator.
```
##### –

```
** The IBM DataPower Gateway operator package contains multiple image groups. To mirror images for Cloud Pak for Integration, use the
ibmdpCp4i image group.
```
##### –

- 3.1 Generate mirror manifests
- 3.2 Authenticate the entitled registry
- 3.3 Authenticate the local registry
- 3.4 Mirror the images
- 3.5 Configure the OpenShift cluster
- 3.6 Mirror Red Hat operators


A _mirror manifest_ is a YAML file that directs the ibm-pak tool what images to mirror, and where to mirror them.

1. Define the environment variable $TARGET_REGISTRY by running the following command:

```
The <target-registry> refers to the registry (hostname and port) where your images are mirrored to and accessed by the oc cluster. For
example: 172.16.0.10:5000.
If you want the images to use a specific namespace in the target registry, you can specify it here, for example: registry.private/cp4i.
```
2. Generate mirror manifests by running the following command:

```
The command generates the following files at ~/.ibm-pak/data/mirror/$OPERATOR_PACKAGE_NAME/$OPERATOR_VERSION:
```
Repeat the process for each operator package you are mirroring.

### 3.2. Authenticate the entitled registry

You must authenticate to the entitled registry to mirror the required images.

1. Export the path to the file which stores the auth credentials that are generated from podman login or docker login. The authentication
    file is typically located at $HOME/.docker/config.json on Linux or %USERPROFILE%/.docker/config.json on Windows:
2. Login to the cp.icr.io registry with podman or docker.
    The username is cp and the password is the IBM entitlement key. To get your entitlement key, go to the Container software library and click
    **Copy** for any key in the list.
    For example:

### 3.3. Authenticate the local registry

```
export TARGET_REGISTRY=<target-registry>
```
```
oc ibm-pak generate mirror-manifests $OPERATOR_PACKAGE_NAME --version $OPERATOR_VERSION $TARGET_REGISTRY --install-method OLM
```
```
▪ If you need to filter for a specific image group, add the parameter --filter <image_group> to this command.
If your registry (for example, GitLab) restricts the number of path separators in the image name, you need to add a parameter and argument
to this command. For more information, see Troubleshooting issues when mirroring images for an air-gapped OpenShift cluster.
```
##### ▪

```
▪ catalog-sources.yaml
▪ catalog-sources-linux-<arch>.yaml (if there are arch specific catalog sources)
▪ image-content-source-policy.yaml
▪ images-mapping.txt
```
```
export REGISTRY_AUTH_FILE=$HOME/.docker/config.json
```
```
podman login cp.icr.ioUsername: cp
Password: <ibm_entitlement_key>
Login Succeeded!
```

You must authenticate to the local registry to mirror the required images.

1. Login to the local registry with podman or docker:

```
Use an account that can write images to the local registry.
```
### 3.4. Mirror the images

Run the following command to copy the images to the local registry. Your device must be connected to both the internet and the restricted
network environment that contains the local registry.

The oc image mirror command starts by planning what images and layers need to be transferred. It can take a couple of minutes before you
start seeing output.
If the local registry is not secured by TLS, or the certificate presented by the local registry is not trusted by your device, add the --insecure
option to the command.
Repeat the process for each operator package you are mirroring.

### 3.5. Configure the OpenShift cluster

1. Log in to your Red Hat OpenShift Container Platform by using the oc CLI.
2. Update the global image pull secret for your cluster.
    Follow the procedure in Updating the global cluster pull secret. These steps enable your cluster to have proper authentication credentials in
    place so that it can pull images from your TARGET_REGISTRY (as specified in the image-content-source-policy.yaml).
3. Create the ImageContentSourcePolicy resource:

```
Verify that the ImageContentSourcePolicy resource is created:
```
```
Verify your OpenShift cluster node status and wait for all nodes to be updated before proceeding:
```
### 3.6. Mirror the Red Hat OpenShift operators

Mirror the following Red Hat OpenShift operators, which are part of the redhat-operators catalog source, as applicable:

```
podman login $TARGET_REGISTRY
```
```
oc image mirror \ -f ~/.ibm-pak/data/mirror/$OPERATOR_PACKAGE_NAME/$OPERATOR_VERSION/images-mapping.txt \
-a $REGISTRY_AUTH_FILE \ --filter-by-os '.*' \
--skip-multiple-scopes \ --max-per-registry=
```
```
oc apply -f ~/.ibm-pak/data/mirror/$OPERATOR_PACKAGE_NAME/$OPERATOR_VERSION/image-content-source-policy.yaml
```
```
oc get imageContentSourcePolicy
```
```
oc get MachineConfigPool -w
```

To mirror these operator images and apply the catalog source, first review Prerequisites for mirroring images for a disconnected installation using
the oc-mirror plugin, then follow the essential steps as described in the Red Hat OpenShift documentation:

1. Configuring credentials that allow images to be mirrored
2. Creating the image set configuration
3. Mirroring an image set in a fully disconnected environment
4. Mirroring images for a disconnected installation using the oc-mirror plugin

For more information, see Mirroring images for a disconnected installation using the oc-mirror plugin.

## Next steps

Now that you have mirrored images for the air-gapped environment, add the catalog sources. See Adding catalog sources to an OpenShift cluster
and follow the steps to log in and export environment variables, then skip to the step for applying the the catalog sources.

```
RedHat Build of Keycloak, if you want to use Cloud Pak foundational services identity and access management. The catalog source must
contain one of these operator channels: stable-v22, stable-v24, or stable-v26.
```
##### –

- cert-manager Operator for Red Hat OpenShift, if you are planning to deploy API Connect cluster, Event Manager, or Event Processing instances.


