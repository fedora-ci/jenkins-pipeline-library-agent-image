#!/usr/bin/env python3

# Simple convertor from the TestingFarm XUnit files into standard JUnit files.


import argparse
import sys
import time

from lxml import etree
from lxml import objectify

import requests


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
    try:
        output.text = cdata
    except ValueError:
        output.text = repr(cdata)


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


def add_error(xml, test_name, logs, classname='tests', docs_url=None, issues_url=None):
    """Add entry for a test error."""
    testcase = etree.SubElement(xml, 'testcase', name=test_name, classname=classname)
    failure = etree.SubElement(
        testcase,
        'error',
        type='ERROR',
        message='Error: "{name}" test failed to run. This is likely an infrastructure issue.\n{about}'.format(
            name=test_name, about=get_about_text(docs_url, issues_url)
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


def has_testcases(xml):
    """Check if given TestingFarm XUnit has at least one testcase.

    :param xml: xml, TF XUnit XML
    :return: bool, True if there is at least one testcase, False otherwise
    """
    if hasattr(xml.testsuite[0], 'testcase'):
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

    tests = 0
    failures = 0
    errors = 0
    skipped = 0

    output_xml = etree.Element('testsuite')

    if not has_testcases(input_xml):
        # likely an infra error; no tests were run so there is nothing to show
        # let's fabricate at least this dummy "infrastructure" test so we can show URLs to docs and issue tracker
        add_error(output_xml, 'infrastructure', 'No tests were run.', issues_url=args.issues_url)
        errors += 1
    else:
        # TODO: can there be more test suites in a single xunit file?
        for testcase in input_xml.testsuite[0].testcase:
            for log in testcase.logs.log:
                if log.attrib['name'].endswith('.log'):
                    logs = get_test_logs(log.attrib['href'])
                    if not logs:
                        logs = '(empty output)'
                    break
                elif log.attrib['name'] == 'log_dir':
                    logs = 'Logs: {logs_url}'.format(logs_url=log.attrib['href'])

            test_name = testcase.attrib['name']
            result = testcase.attrib['result'].lower()

            tests += 1

            if result in ('passed', 'pass'):
                add_success(output_xml, test_name, logs, docs_url=args.docs_url, issues_url=args.issues_url)
            elif result in ('failed', 'fail'):
                add_failure(output_xml, test_name, logs, docs_url=args.docs_url, issues_url=args.issues_url)
                failures += 1
            elif result in ('error', 'errored'):
                add_error(output_xml, test_name, logs, issues_url=args.issues_url)
                errors += 1
            elif result in ('skipped', 'skip'):
                add_skipped(output_xml, test_name, logs, docs_url=args.docs_url, issues_url=args.issues_url)
                skipped += 1

    output_xml.attrib['tests'] = str(tests)
    output_xml.attrib['failures'] = str(failures)
    output_xml.attrib['errors'] = str(errors)
    output_xml.attrib['skipped'] = str(skipped)

    objectify.deannotate(output_xml, cleanup_namespaces=True, xsi_nil=True)
    print(etree.tostring(output_xml, pretty_print=True).decode())


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
