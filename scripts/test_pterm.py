#! /usr/bin/env python3:

import tempfile
from pterm import get_aws_profiles
from pterm import create_aws_profiles
from pterm import sort_aws_config


def create_config(contents):
    temp = tempfile.NamedTemporaryFile(mode='w', delete=False)
    temp.write(contents)
    return temp.name


def test_get_aws_profiles():
    cases = [
        (
            '''
            [profile 1]
            ''',
            [['1', None, None, None, False, None]],
        ),
        (
            '''
            [profile 2]
            role_arn = arn:partition:service:region:account:resource
            ''',
            [
                ['2', 'account', 'resource', None, False, None]
            ],
        ),
        (
            '''
            [profile 3]

            [profile 4]
            source_profile = 3
            ''',
            [
                ['3', None, None, None, False, 'log-4'],
                ['4', None, None, '3', False, None]
            ],
        ),
    ]

    for case, result in cases:
        config = get_aws_profiles(create_config(case))
        assert result == config


def test_create_aws_profiles():
    case = '''
            [profile 1]
           '''
    profiles = create_aws_profiles(create_config(case))
    names = [x['Name'] for x in profiles]
    assert names == list(set(names))

    case = '''
            [profile 2]
            [profile 3]
            source_profile = 2
            '''
    profiles = create_aws_profiles(create_config(case))
    assert profiles[0]['Name'] == '2'
    assert profiles[1]['Name'] == 'login-2'
    assert profiles[2]['Name'] == '3'

    case = '''
            [profile 4]
            azure_tenant_id = foobar
            [profile 5]
            source_profile = 4
            '''
    profiles = create_aws_profiles(create_config(case), azure_path)
    assert profiles[1]['Name'] == 'login-4'
    assert 'aws-azure-login' in profiles[1]['Command']


def azure_path():
    return '/some/path'


def test_sort_aws_config():
    case = '''
        [profile b]
        [profile a]
        [profile c]
    '''

    config = create_config(case)
    sort_aws_config(config)

    new_config = [
        x.rstrip() for x in tuple(open(config, 'r')) if x.rstrip()
    ]
    expected = sorted(
        [x.strip() for x in case.split('\n') if x.strip()]
    )
    assert new_config == expected


def test_sort_aws_config_dry():
    case = '''
        [profile b]
        [profile a]
        [profile c]
    '''
    config = create_config(case)
    sort_aws_config(config, dry=True)

    new_config = [
        x.strip() for x in tuple(open(config, 'r')) if x.strip()
    ]
    expected = [x.strip() for x in case.split('\n') if x.strip()]

    assert new_config == expected
