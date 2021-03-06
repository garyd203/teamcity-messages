import os
import subprocess

import pytest

import virtual_environments
from service_messages import ServiceMessage, assert_service_messages


@pytest.fixture(scope='module', params=["nose", "nose==1.2.1", "nose==1.3.1"])
def venv(request):
    """
    Prepares a virtual environment for nose.
    :rtype : virtual_environments.VirtualEnvDescription
    """
    return virtual_environments.prepare_virtualenv([request.param])


def test_hierarchy(venv):
    output = run(venv, 'hierarchy')
    test_name = 'namespace1.namespace2.testmyzz.test'
    assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': test_name, 'captureStandardOutput': 'true', 'flowId': test_name}),
            ServiceMessage('testFinished', {'name': test_name, 'flowId': test_name}),
        ])


def test_doctests(venv):
    output = run(venv, 'doctests', options="--with-doctest")
    test_name = 'doctests.namespace1.d.multiply'
    assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': test_name, 'flowId': test_name}),
            ServiceMessage('testFinished', {'name': test_name, 'flowId': test_name}),
        ])


def test_docstrings(venv):
    output = run(venv, 'docstrings')
    test_name = 'testa.test_func (My cool test_name)'
    assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': test_name, 'flowId': test_name}),
            ServiceMessage('testFinished', {'name': test_name, 'flowId': test_name}),
        ])


def test_skip(venv):
    output = run(venv, 'skiptest')
    test_name = 'testa.test_func'
    assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': test_name, 'flowId': test_name}),
            ServiceMessage('testIgnored', {'name': test_name, 'message': 'SKIPPED: my skip', 'flowId': test_name}),
            ServiceMessage('testFinished', {'name': test_name, 'flowId': test_name}),
        ])


def test_coverage(venv):
    venv_with_coverage = virtual_environments.prepare_virtualenv(venv.packages + ["coverage==3.7.1"])

    coverage_file = os.path.join(virtual_environments.get_vroot(), "coverage-temp.xml")

    output = run(venv_with_coverage, 'coverage', options="--with-coverage --cover-erase --cover-tests --cover-xml --cover-xml-file=\"" + coverage_file + "\"")
    assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': 'testa.test_mycode'}),
            ServiceMessage('testFinished', {'name': 'testa.test_mycode'}),
        ])

    f = open(coverage_file, "rb")
    content = str(f.read())
    f.close()

    assert content.find('<line hits="1" number="2"/>') > 0


def test_deprecated(venv):
    output = run(venv, 'deprecatedtest')
    test_name = 'testa.test_func'
    assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': test_name, 'flowId': test_name}),
            ServiceMessage('testIgnored', {'name': test_name, 'message': 'Deprecated', 'flowId': test_name}),
            ServiceMessage('testFinished', {'name': test_name, 'flowId': test_name}),
        ])


def test_generators(venv):
    output = run(venv, 'generators')
    assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': 'testa.test_evens(0, 0, |\'_|\')'}),
            ServiceMessage('testFinished', {'name': 'testa.test_evens(0, 0, |\'_|\')'}),
            ServiceMessage('testStarted', {'name': "testa.test_evens(1, 3, |'_|')"}),
            ServiceMessage('testFinished', {'name': "testa.test_evens(1, 3, |'_|')"}),
            ServiceMessage('testStarted', {'name': "testa.test_evens(2, 6, |'_|')"}),
            ServiceMessage('testFinished', {'name': "testa.test_evens(2, 6, |'_|')"}),
        ])


def test_generators_class(venv):
    output = run(venv, 'generators_class')
    assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': 'testa.TestA.test_evens(0, 0, |\'_|\')'}),
            ServiceMessage('testFinished', {'name': 'testa.TestA.test_evens(0, 0, |\'_|\')'}),
            ServiceMessage('testStarted', {'name': "testa.TestA.test_evens(1, 3, |'_|')"}),
            ServiceMessage('testFinished', {'name': "testa.TestA.test_evens(1, 3, |'_|')"}),
            ServiceMessage('testStarted', {'name': "testa.TestA.test_evens(2, 6, |'_|')"}),
            ServiceMessage('testFinished', {'name': "testa.TestA.test_evens(2, 6, |'_|')"}),
        ])


def test_pass(venv):
    output = run(venv, 'nose-guinea-pig.py', 'GuineaPig', 'test_pass')
    assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': 'nose-guinea-pig.GuineaPig.test_pass'}),
            ServiceMessage('testFinished', {'name': 'nose-guinea-pig.GuineaPig.test_pass'}),
        ])


def test_fail(venv):
    output = run(venv, 'nose-guinea-pig.py', 'GuineaPig', 'test_fail')
    test_name = 'nose-guinea-pig.GuineaPig.test_fail'
    ms = assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': test_name}),
            ServiceMessage('testFailed', {'name': test_name, 'flowId': test_name}),
            ServiceMessage('testFinished', {'name': test_name}),
        ])

    assert ms[1].params['details'].find("Traceback") == 0
    assert ms[1].params['details'].find("2 * 2 == 5") > 0


def test_setup_module_error(venv):
    output = run(venv, 'setup_module_error')
    test_name = 'namespace2.testa.setup'
    ms = assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': test_name}),
            ServiceMessage('testFailed', {'name': test_name, 'flowId': test_name}),
            ServiceMessage('testFinished', {'name': test_name}),
        ])
    assert ms[1].params['details'].find("Traceback") == 0
    assert ms[1].params['details'].find("AssertionError") > 0


def test_setup_class_error(venv):
    output = run(venv, 'setup_class_error')
    test_name = 'testa.TestXXX.setup'
    ms = assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': test_name}),
            ServiceMessage('testFailed', {'name': test_name, 'flowId': test_name, 'message': 'error in setup context'}),
            ServiceMessage('testFinished', {'name': test_name}),
        ])
    assert ms[1].params['details'].find("Traceback") == 0
    assert ms[1].params['details'].find("RRR") > 0


def test_setup_package_error(venv):
    output = run(venv, 'setup_package_error')
    test_name = 'namespace2.setup'
    ms = assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': test_name}),
            ServiceMessage('testFailed', {'name': test_name, 'flowId': test_name, 'message': 'error in setup context'}),
            ServiceMessage('testFinished', {'name': test_name}),
        ])
    assert ms[1].params['details'].find("Traceback") == 0
    assert ms[1].params['details'].find("AssertionError") > 0


def test_setup_function_error(venv):
    output = run(venv, 'setup_function_error')
    test_name = 'testa.test'
    ms = assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': test_name}),
            ServiceMessage('testFailed', {'name': test_name, 'flowId': test_name}),
            ServiceMessage('testFinished', {'name': test_name}),
        ])
    assert ms[1].params['details'].find("Traceback") == 0
    assert ms[1].params['details'].find("AssertionError") > 0


def test_teardown_module_error(venv):
    output = run(venv, 'teardown_module_error')
    test_name = 'namespace2.testa.teardown'
    ms = assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': 'namespace2.testa.test_mycode'}),
            ServiceMessage('testFinished', {'name': 'namespace2.testa.test_mycode'}),
            ServiceMessage('testStarted', {'name': test_name}),
            ServiceMessage('testFailed', {'name': test_name, 'flowId': test_name, 'message': 'error in teardown context'}),
            ServiceMessage('testFinished', {'name': test_name}),
        ])
    assert ms[3].params['details'].find("Traceback") == 0
    assert ms[3].params['details'].find("AssertionError") > 0


def test_teardown_class_error(venv):
    output = run(venv, 'teardown_class_error')
    test_name = 'testa.TestXXX.teardown'
    ms = assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': 'testa.TestXXX.runTest'}),
            ServiceMessage('testFinished', {'name': 'testa.TestXXX.runTest'}),
            ServiceMessage('testStarted', {'name': test_name}),
            ServiceMessage('testFailed', {'name': test_name, 'flowId': test_name, 'message': 'error in teardown context'}),
            ServiceMessage('testFinished', {'name': test_name}),
        ])
    assert ms[3].params['details'].find("Traceback") == 0
    assert ms[3].params['details'].find("RRR") > 0


def test_teardown_package_error(venv):
    output = run(venv, 'teardown_package_error')
    test_name = 'namespace2.teardown'
    ms = assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': 'namespace2.testa.test_mycode'}),
            ServiceMessage('testFinished', {'name': 'namespace2.testa.test_mycode'}),
            ServiceMessage('testStarted', {'name': test_name}),
            ServiceMessage('testFailed', {'name': test_name, 'flowId': test_name, 'message': 'error in teardown context'}),
            ServiceMessage('testFinished', {'name': test_name}),
        ])
    assert ms[3].params['details'].find("Traceback") == 0
    assert ms[3].params['details'].find("AssertionError") > 0


def test_teardown_function_error(venv):
    output = run(venv, 'teardown_function_error')
    test_name = 'testa.test'
    ms = assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': test_name}),
            ServiceMessage('testFailed', {'name': test_name, 'flowId': test_name}),
            ServiceMessage('testFinished', {'name': test_name}),
        ])
    assert ms[1].params['details'].find("Traceback") == 0
    assert ms[1].params['details'].find("AssertionError") > 0


def test_fail_with_msg(venv):
    output = run(venv, 'nose-guinea-pig.py', 'GuineaPig', 'test_fail_with_msg')
    test_name = 'nose-guinea-pig.GuineaPig.test_fail_with_msg'
    ms = assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': test_name}),
            ServiceMessage('testFailed', {'name': test_name, 'flowId': test_name}),
            ServiceMessage('testFinished', {'name': test_name}),
        ])
    assert ms[1].params['details'].find("Bitte keine Werbung") > 0


def test_fail_output(venv):
    output = run(venv, 'nose-guinea-pig.py', 'GuineaPig', 'test_fail_output')
    test_name = 'nose-guinea-pig.GuineaPig.test_fail_output'
    assert_service_messages(
        output,
        [
            ServiceMessage('testStarted', {'name': test_name, 'flowId': test_name}),
            ServiceMessage('testStdOut', {'name': test_name, 'out': 'Output line 1|nOutput line 2|nOutput line 3|n', 'flowId': test_name}),
            ServiceMessage('testFailed', {'name': test_name, 'flowId': test_name}),
            ServiceMessage('testFinished', {'name': test_name, 'flowId': test_name}),
        ])


def test_fail_big_output(venv):
    output = run(venv, 'nose-guinea-pig.py', 'GuineaPig', 'test_fail_big_output')
    test_name = 'nose-guinea-pig.GuineaPig.test_fail_big_output'

    full_line = 'x' * 50000
    leftovers = 'x' * (1024 * 1024 - 50000 * 20)

    assert_service_messages(
        output,
        [ServiceMessage('testStarted', {})] +
        [ServiceMessage('testStdOut', {'out': full_line, 'flowId': test_name})] * 20 +
        [ServiceMessage('testStdOut', {'out': leftovers, 'flowId': test_name})] +
        [ServiceMessage('testFailed', {'name': test_name, 'flowId': test_name})] +
        [ServiceMessage('testFinished', {})]
    )


def run(venv, file, clazz=None, test=None, options=""):
    env = virtual_environments.get_clean_system_environment()
    env['TEAMCITY_VERSION'] = "0.0.0"

    if clazz:
        clazz_arg = ":" + clazz
    else:
        clazz_arg = ""

    if test:
        test_arg = "." + test
    else:
        test_arg = ""

    command = os.path.join(venv.bin, 'nosetests') + \
        " -v " + options + " " + \
        os.path.join('tests', 'guinea-pigs', 'nose', file) + clazz_arg + test_arg
    print("RUN: " + command)
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, shell=True)
    output = "".join([x.decode() for x in proc.stdout.readlines()])
    proc.wait()

    print("OUTPUT:" + output.replace("#", "*"))

    return output
