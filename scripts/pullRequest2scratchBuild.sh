#!/bin/bash

# Scratch-build pull requests. And add enough metadata so it is later posible
# to map such scratch-builds back to pull requests.
#
# Note this is an ugly hack. The way the tracking works is by submitting a SRPM
# to Koji. The SRPM has a carefurly crafted name. The name is preserved by Koji
# and thus can be later "decoded" to get the information about the original
# pull request.
#
# SRPM naming schema:
# fedora-ci_<pr-uid>_<pr_commit_hash>_<pr_comment_id>;<fork-repo-full-name*>.f34.src.rpm
# Note "fork-repo-full-name" cannot contain URL unsafe characters, so all slashes
# are replaced with colons. I.e. "forks/user/rpms/repo" would be encoded as "forks:user:rpms:repo"
# in the SRPM name.

set -e
set -x


if [ -d "${REPO_NAME}" ]; then
    rm -Rf ${REPO_NAME}
fi

# This is a standard pull request; clone it and switch to the pull request branch
fedpkg clone -a ${REPO_FULL_NAME}
git fetch https://src.fedoraproject.org/${REPO_FULL_NAME}.git refs/pull/${PR_ID}/head:pr${PR_ID}
git checkout pr${PR_ID}

cd ${REPO_NAME}

srpm_path=$(fedpkg --release ${RELEASE_ID} srpm | grep 'Wrote:' | awk '{ print $2 }')
srpm_name=$(basename ${srpm_path})
new_srpm_name="fedora-ci_${PR_UID}_${PR_COMMIT}_${PR_COMMENT};${SOURCE_REPO_FULL_NAME//\//:}.${RELEASE_ID}.src.rpm"
mv ${srpm_name} ${new_srpm_name}

kinit -k -t ${KOJI_KEYTAB} ${KRB_PRINCIPAL}

fedpkg scratch-build --nowait --target ${RELEASE_ID} --srpm ${new_srpm_name}
