#!/bin/bash

# Scratch-build pull requests in Koji.

# Required environment variables:
# KOJI_KEYTAB - path to the keytab that can be used to build packages in Koji
# KRB_PRINCIPAL - kerberos principal
# ARCH_OVERRIDE - only build for specified architectures (example: "x86_64,i686")

workdir=${PWD}

if [ $# -ne 3 ]; then
    echo "Usage: $0 <koji|brew> <target> <scm url>"
    exit 101
fi

koji_log=${workdir}/koji.log
koji_url=${workdir}/koji_url

set -e
set -x

rm -f ${fedpkg_log}
rm -f ${koji_url}

profile=${1}
target=${2}
source_url=${3}

if [ -z "${KOJI_KEYTAB}" ]; then
    echo "Missing keytab, cannot continue..."
    exit 101
fi

if [ -z "${KRB_PRINCIPAL}" ]; then
    echo "Missing kerberos principal, cannot continue..."
    exit 101
fi

kinit -k -t ${KOJI_KEYTAB} ${KRB_PRINCIPAL}

koji -p ${profile} build --scratch --fail-fast ${ARCH_OVERRIDE:+--arch-override=$ARCH_OVERRIDE} --nowait ${target} ${source_url} > ${koji_log}
cat ${koji_log}

cat ${koji_log} | grep '^Task info: ' | awk '{ print $3 }' > ${koji_url}

task_id=$(cat ${koji_log} | grep '^Created task: ' | awk '{ print $3 }')

koji -p ${profile} watch-task ${task_id}
