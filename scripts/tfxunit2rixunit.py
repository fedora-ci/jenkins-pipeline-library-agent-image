#!/usr/bin/env python3

# Read TestingFarm XUnit and fetch real rpminspect XUnit from the log dir.


import argparse
from lxml import objectify
import time
import requests


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


def main(args):
    """Read TestingFarm XUnit and fetch real rpminspect XUnit from the log dir.

    The results will be printed to the stdout.

    :param args: parsed args
    :return: None
    """
    tf_xunit = load_tf_xunit(args.xunit_input[0])
    input_xml = objectify.fromstring(tf_xunit)

    for testcase in input_xml.testsuite[0].testcase:
        for log in testcase.logs.log:
            if log.attrib['name'] == 'log_dir':
                log_dir = log.attrib['href']
                root_dir = log_dir.split('/execute/data/')[0]
                xunit_url = root_dir + '/discover/default/tests/rpminspect_stdout'
                xunit = get_test_logs(xunit_url)
                break

    print(xunit.decode())


def parse_args():
    """Parse arguments."""
    parser = argparse.ArgumentParser(description='Convert TestingFarm XUnit file to the standard JUnit.')
    parser.add_argument('xunit_input', nargs=1, help='TestingFarm XUnit file')

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    main(args)
