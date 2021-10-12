#!/usr/bin/env python3

# Simple convertor from the TestingFarm XUnit files into standard JUnit files.


import argparse
import sys
import time
import unicodedata
import re
import os
import itertools

from lxml import etree
from lxml import html
from lxml import objectify

import requests


# build regular expression to find unicode control (non-printable) characters in a string (minus CR-LF)
control_chars = ''.join([chr(x) for x in itertools.chain(range(0x00,0x20), range(0x7f,0xa0)) if x not in [0x0d, 0x0a]])
control_char_re = re.compile('[%s]' % re.escape(control_chars))

# guest-setup stage priorities, used to determine which guest-setup stage was the last to fail
# the order in logs is not sorted, so we cannot rely on the order
stage_prorities = {
    'pre_artifact_installation': 0,
    'artifact_installation': 1,
    'post_artifact_installation': 2
}

def remove_control_chars(s):
    """Remove non-printable control characters from a string."""
    return control_char_re.sub('', s)


def to_cdata(output, text):
    """Prepare text (logs) to be part of the final JUnit.

    TODO: I *think* some escaping will be needed here (?)

    :param text: str or bytes, text to process
    :return: str, text that can be safely added to the JUnit file
    """
    if isinstance(text, str):
        cdata = '{output}'.format(output=text)
    else:
        cdata = '{output}'.format(output=text.decode())

    output.text = remove_control_chars(cdata)


def add_success(xml, test_name, logs, classname='tests', docs_url=None, issues_url=None):
    """Add entry for a successful test."""
    testcase = etree.SubElement(xml, 'testcase', name=test_name, classname=classname)
    output = etree.SubElement(testcase, 'system-out')
    to_cdata(output, logs)


def add_failure(xml, test_name, logs, classname='tests', docs_url=None, issues_url=None):
    """Add entry for a failed test."""
    testcase = etree.SubElement(xml, 'testcase', name=test_name, classname=classname)
    failure = etree.SubElement(
        testcase,
        'failure',
        type='FAIL',
        message='Test "{name}" failed.\n{about}'.format(name=test_name, about=get_about_text(docs_url, issues_url))
    )
    output = etree.SubElement(testcase, 'system-out')
    to_cdata(output, logs)


def add_package_installation_failure(xml, test_name, logs, classname='environment preparation', docs_url=None, issues_url=None):
    """Add entry for a test error."""
    testcase = etree.SubElement(xml, 'testcase', name=test_name, classname=classname)
    failure = etree.SubElement(
        testcase,
        'failure',
        message='Failed to install tested packages.\n{about}'.format(about=get_about_text(docs_url, issues_url))
    )

    for log in logs:
        output = etree.SubElement(testcase, 'system-out')
        to_cdata(output, log)


def add_error(xml, test_name, logs, message, classname='tests', docs_url=None, issues_url=None):
    """Add entry for a test error."""
    testcase = etree.SubElement(xml, 'testcase', name=test_name, classname=classname)
    failure = etree.SubElement(
        testcase,
        'error',
        type='ERROR',
        message='{message}\n{about}'.format(
            message=message, about=get_about_text(docs_url, issues_url)
        )
    )
    output = etree.SubElement(testcase, 'system-out')
    to_cdata(output, logs)


def add_skipped(xml, test_name, logs, classname='tests', docs_url=None, issues_url=None):
    """Add entry for a skipped test."""
    testcase = etree.SubElement(root, 'testcase', name=test_name, classname=classname)
    failure = etree.SubElement(
        testcase,
        'skipped',
        type='SKIPPED',
        message='Test "{name}" was skipped.\n{about}'.format(
            name=test_name, about=get_about_text(docs_url, issues_url)
        )
    )
    output = etree.SubElement(testcase, 'system-out')
    to_cdata(output, logs)


def get_about_text(docs_url, issues_url):
    """
    Construct a short "About" paragraph containing docs and/or issues URL.

    :param docs_url: str, URL for docs
    :param issues_url: str, URL for issues
    :return: str, "about" text
    """
    docs_text = ''
    issues_text = ''
    if docs_url:
        docs_text = 'Find out more about this test in the documentation: {url}\n'.format(url=docs_url)
    if issues_url:
        issues_text = 'Found a bug? Please open an issue in the issue tracker: {url}\n'.format(url=issues_url)
    about_text = '''
{docs_text}{issues_text}
'''.format(docs_text=docs_text, issues_text=issues_text)
    return about_text


def load_tf_xunit(tf_xunit_path):
    """Load TestingFarm XUnit file.

    :param tf_xunit_path: str, path to the TF Xunit file
    :return: str, content of the XUnit file
    """
    with open(tf_xunit_path) as f:
        # remove escaping which makes the file invalid for xml parsers
        tf_xunit = f.read().replace('\\"', '"')
    return tf_xunit

def get_artifact_installation_logs(url):
    """Try to fetch test logs from the given URL.

    Try couple times and the logs cannot be fetched,
    just provide the URL (maybe the logs will be available later).

    :param url: str, URL to the test logs
    :return: List[str], test logs, with steps as lists
    """
    retry_count = 10
    while retry_count:
        response = requests.get(url)
        if response.status_code in (404, 429, 500, 502, 503, 504):
            # Note 404 is in the list because I am not sure if logs are already synced
            # in the artifacts storage when Testing Farm says that the testing is done.
            retry_count -= 1
            time.sleep(10)
            continue
        else:
            artifact_installation_html = response.content
            break
    else:
        return 'Logs: {url}'.format(url=url)

    index = html.fromstring(artifact_installation_html)

    logs = index.xpath('//a')[1:]

    outputs = []

    for log in logs:
        logname = log.attrib['href']
        outputs.append('Stage: {name}\n\n{log}'.format(
            name=logname,
            log=get_test_logs(os.path.join(url, logname)).decode()
        ))

    return outputs

def get_test_logs(url):
    """Try to fetch test logs from the given URL.

    Try couple times and the logs cannot be fetched,
    just provide the URL (maybe the logs will be available later).

    :param url: str, URL to the test logs
    :return: str, test logs
    """
    retry_count = 10
    while retry_count:
        response = requests.get(url)
        if response.status_code in (404, 429, 500, 502, 503, 504):
            # Note 404 is in the list because I am not sure if logs are already synced
            # in the artifacts storage when Testing Farm says that the testing is done.
            retry_count -= 1
            time.sleep(10)
            continue
        else:
            logs = response.content
            break
    else:
        logs = 'Logs: {url}'.format(url=url)
    return logs


def parse_testcases(testsuite, xml):
    """Parse testcases into the standard JUnit.

    The results will be printed to the stdout.

    :param testsuite: Testuite being parsed
    :param xml: XML document to parse
    :return: parsed xml
    """

    if not hasattr(testsuite, 'testcase'):
        return xml

    tests = 0
    failures = 0
    errors = 0
    skipped = 0

    for testcase in testsuite.testcase:
        for log in testcase.logs.log:
            if log.attrib['name'].endswith('.log') or log.attrib['name'].endswith('output.txt'):
                logs = get_test_logs(log.attrib['href'])
                if not logs:
                    logs = '(empty output)'
                break
            elif log.attrib['name'] == 'log_dir':
                logs = 'Logs: {logs_url}'.format(logs_url=log.attrib['href'])

        test_name = testcase.attrib['name']
        result = testcase.attrib['result'].lower()

        tests += 1

        if result in ('passed', 'pass', 'pass:'):
            add_success(xml, test_name, logs, docs_url=args.docs_url, issues_url=args.issues_url)
        elif result in ('failed', 'fail', 'fail:', 'needs_inspection'):
            add_failure(xml, test_name, logs, docs_url=args.docs_url, issues_url=args.issues_url)
            failures += 1
        elif result in ('error', 'errored', 'error:'):
            add_failure(xml, test_name, logs, docs_url=args.docs_url, issues_url=args.issues_url)
            failures += 1
        elif result in ('skipped', 'skip', 'skip:'):
            add_skipped(xml, test_name, logs, docs_url=args.docs_url, issues_url=args.issues_url)
            skipped += 1

        xml.attrib['tests'] = str(tests)
        xml.attrib['failures'] = str(failures)
        xml.attrib['errors'] = str(errors)
        xml.attrib['skipped'] = str(skipped)

    return xml

def parse_package_installation(testsuite, xml):
    """Parse testcases into the standard JUnit.

    The results will be printed to the stdout.

    :param testsuite: Testsuite being parsed
    :param xml: XML document to add results
    :return: XML document extended with packages installation logs
    """

    # handle undefined result, which means we failed before running tests
    # go in reverse order of the stages, if a stage fails, it is the last one
    # if all went well, this is not interesting for the user :)

    if 'result' not in testsuite.attrib or testsuite.attrib['result'] != 'undefined':
        return xml

    # choose the latest stage
    try:
        log = max(
            (stage_prorities[log.attrib['guest-setup-stage']], log)
            for log in testsuite.logs.log
        )[1]
    except (KeyError, IndexError):
        # no logs, no guest-setup stages
        return xml

    # post_artifact_installation installation problem
    if log.attrib['guest-setup-stage'] == 'pre_artifact_installation':
        logs = get_test_logs(log.attrib['href'])
        add_error(
            xml, 'package installation', logs,
            'Failed to prepare test environment before package installation.',
            docs_url=args.docs_url, issues_url=args.issues_url
        )
        xml.attrib['error'] = '1'
    # artifact installation problem
    elif log.attrib['guest-setup-stage'] == 'artifact_installation':
        logs = get_artifact_installation_logs(log.attrib['href'])
        add_package_installation_failure(
            xml, 'package installation', logs,
            docs_url=args.docs_url, issues_url=args.issues_url)
        xml.attrib['failures'] = '1'
    # post_artifact_installation installation problem
    elif log.attrib['guest-setup-stage'] == 'post_artifact_installation':
        logs = get_test_logs(log.attrib['href'])
        add_error(
            xml, 'package installation', logs,
            'Failed to prepare test environment after package installation.',
            docs_url=args.docs_url, issues_url=args.issues_url
        )
        xml.attrib['error'] = '1'

    return xml


def has_testcases(xml):
      """Check if given TestingFarm XUnit has at least one testcase.

      :param xml: xml with testsuite
      :return: bool, True if there is at least one testcase, False otherwise
      """

      # if testsuite has a child, it means a testcase is present
      if len(xml) > 0:
          return True

      return False


def main(args):
    """Convert TestingFarm XUnit into the standard JUnit.

    The results will be printed to the stdout.

    :param args: parsed args
    :return: None
    """
    tf_xunit = load_tf_xunit(args.xunit_input[0])
    input_xml = objectify.fromstring(tf_xunit)

    root_output_xml = etree.Element('testsuites')

    output_xml = etree.Element('testsuite')

    for count, testsuite in enumerate(input_xml.testsuite):
        output_xml = etree.SubElement(root_output_xml, 'testsuite')

        # add testsuite name
        try:
            output_xml.attrib['name'] = testsuite.attrib['name']
        except KeyError:
            output_xml.attrib['name'] = 'testsuite {}'.format(count)

        output_xml = parse_package_installation(testsuite, output_xml)

        output_xml = parse_testcases(testsuite, output_xml)

        if not has_testcases(output_xml):
            # likely an infra error; no tests were run so there is nothing to show
            # let's fabricate at least this dummy "infrastructure" test so we can show URLs to docs and issue tracker
            add_error(
                output_xml, 'infrastructure', 'No tests were run.',
                'Error: tests failed to run. This is likely an infrastructure issue.',
                issues_url=args.issues_url
            )
            output_xml.attrib['errors'] = '1'

    objectify.deannotate(root_output_xml, cleanup_namespaces=True, xsi_nil=True)
    print(etree.tostring(root_output_xml, pretty_print=True).decode())

def parse_args():
    """Parse arguments."""
    parser = argparse.ArgumentParser(description='Convert TestingFarm XUnit file to the standard JUnit.')
    parser.add_argument('xunit_input', nargs=1, help='TestingFarm XUnit file')
    parser.add_argument('--docs-url', dest='docs_url', help='URL to the docs')
    parser.add_argument('--issues-url', dest='issues_url', default='https://pagure.io/fedora-ci/general/issues', help='URL where to file issues')

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    main(args)
