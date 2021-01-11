#!/bin/bash

# Scratch-build pull requests in Koji.

# Required environment variables:
# KOJI_KEYTAB - path to the keytab that can be used to build packages in Koji
# KRB_PRINCIPAL - kerberos principal
# ARCH_OVERRIDE - only build for specified architectures (example: "x86_64,i686")


if [ $# -ne 4 ]; then
    echo "Usage: $0 <koji|brew> <wait|nowait> <target> <scm url>"
    exit 101
fi

set -e
set -x

profile=${1}
wait_method=${2}
target=${3}
source_url=${4}

if [ -z "${KOJI_KEYTAB}" ]; then
    echo "Missing keytab, cannot continue..."
    exit 101
fi

if [ -z "${KRB_PRINCIPAL}" ]; then
    echo "Missing kerberos principal, cannot continue..."
    exit 101
fi

kinit -k -t ${KOJI_KEYTAB} ${KRB_PRINCIPAL}

koji -p ${profile} build --scratch ${ARCH_OVERRIDE:+--arch-override=$ARCH_OVERRIDE} --${wait_method} ${target} ${source_url}
