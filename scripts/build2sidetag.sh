#!/bin/bash

# Scratch-build pull requests in Koji.

# Required environment variables:
# KOJI_KEYTAB - path to the keytab that can be used to build packages in Koji
# KRB_PRINCIPAL - kerberos principal

workdir=${PWD}

if [ $# -ne 2 ]; then
    echo "Usage: $0  <base-tag> <nvr>"
    exit 101
fi

request_log=${workdir}/request.log
sidetag_name=${workdir}/sidetag_name

set -e
set -x

rm -f ${request_log}
rm -f ${sidetag_name}

base_tag=${1}
nvr=${2}

if [ -z "${KOJI_KEYTAB}" ]; then
    echo "Missing keytab, cannot continue..."
    exit 101
fi

if [ -z "${KRB_PRINCIPAL}" ]; then
    echo "Missing kerberos principal, cannot continue..."
    exit 101
fi

kinit -k -t ${KOJI_KEYTAB} ${KRB_PRINCIPAL}

fedpkg request-side-tag --base-tag ${base_tag} > request_log
cat ${request_log}

sidetag_name=$(cat ${request_log} | grep ') created.$' | awk -F\' '{ print $2 }'

echo ${sidetag_name} > ${sidetag_name}

koji tag ${sidetag_name} ${nvr}
