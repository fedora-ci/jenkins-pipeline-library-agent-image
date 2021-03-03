#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

# Meh, nginx cannot work with relative paths, so use a known /tmp location for hosting the test data
# Note that this is hardcoded in nginx/nginx.conf
tmp_webroot=/tmp/xunit-data-webroot
tfxunit2junit=../../../scripts/tfxunit2junit.py

assert_test() {
    rlRun "$tfxunit2junit results/$1.xml | tee $output"
    rlRun "diff results/$1.xml.expect $output"
}

rlJournalStart
    rlPhaseStartSetup
        rlRun "set -o pipefail"
        rlRun "cp -rf webroot $tmp_webroot"
        rlRun "(cd $tmp_webroot && tar xf *.tgz)"
        rlRun "nginx -c $(pwd)/nginx/nginx.conf"
        rlRun "curl localhost:9876"
        rlRun "output=$(mktemp)"
    rlPhaseEnd

    rlPhaseStartTest "errors - guest-setup"
        assert_test error-artifact-installation
        assert_test error-post-artifact-installation
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "pkill nginx"
        rlRun "rm -rf $tmp_webroot $output"
    rlPhaseEnd
rlJournalEnd
