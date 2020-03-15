#! /usr/bin/env python3:

import tempfile
from pterm import aws_config_to_profiles
from pterm import create_aws_profiles
from pterm import sort_aws_config
from pterm import triggers
from pterm import create_k8s_profile
from pterm import find_source_profile
import re
import os
import yaml


def create_config(contents):
    temp = tempfile.NamedTemporaryFile(mode='w', delete=False)
    temp.write(contents)
    return temp.name


def test_aws_config_to_profiles():
    cases = [
        (
            '''
            [profile 1]
            ''',
            {
                '1': {
                    'name': '1',
                    'account': None,
                    'role': None,
                    'azure': False,
                    'source_profile': None,
                },
            },
        ),
        (
            '''
            [profile 2]
            role_arn = arn:partition:service:region:account:resource
            ''',
            {
                '2': {
                    'name': '2',
                    'account': 'account',
                    'role': 'resource',
                    'source_profile': None,
                    'azure': False,
                },
            },
        ),
        (
            '''
            [profile 3]

            [profile 4]
            source_profile = 3
            ''',
            {
                '3': {
                    'name': '3',
                    'account': None,
                    'role': None,
                    'source_profile': None,
                    'azure': False,
                },
                '4': {
                    'name': '4',
                    'account': None,
                    'role': None,
                    'source_profile': '3',
                    'azure': False,
                },
            },
        ),
        (
            '''
            [profile 5]
            azure_tenant_id = foo
            [profile 6]
            source_profile = 5
            ''',
            {
                '5': {
                    'name': '5',
                    'account': None,
                    'role': None,
                    'source_profile': None,
                    'azure': True,
                },
                '6': {
                    'name': '6',
                    'account': None,
                    'role': None,
                    'source_profile': '5',
                    'azure': False,
                },
            },
        ),
    ]

    for case, result in cases:
        config = aws_config_to_profiles(create_config(case))
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
    assert profiles[1]['Name'] == '3'
    assert profiles[2]['Name'] == 'login-2'

    case = '''
            [profile 4]
            azure_tenant_id = foobar
            [profile 5]
            source_profile = 4
            '''
    profiles = create_aws_profiles(create_config(case), azure_path)
    assert profiles[2]['Name'] == 'login-4'
    assert 'aws-azure-login' in profiles[2]['Command']
    assert f'PATH={azure_path()}' in profiles[2]['Command']
    assert 'AWS_PROFILE=4' in profiles[2]['Command']
    assert profiles[1]['Keyboard Map']['0x61-0x80000']['Text'] == 'login-4'


def test_triggers():
    id_rsa_re = [
        x for x in triggers()
        if x['parameter'] == 'id_rsa'
    ][0]['regex']

    cases = [
        # when git push
        f"Enter passphrase for key '{os.getenv('HOME')}/.ssh/id_rsa",
        # when ssh-add
        f"Enter passphrase for {os.getenv('HOME')}/.ssh/id_rsa",
    ]

    for case in cases:
        assert re.search(id_rsa_re, case) is not None


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


def test_create_k8s_profiles():
    case = '''
        [profile aws-profile]
        source_profile = source-profile
        [profile source-profile]
    '''
    aws_profiles = create_aws_profiles(create_config(case), azure_path)

    config = cluster_config('foo')
    profile = create_k8s_profile(config, '/dev/null', aws_profiles)
    assert 'AWS_PROFILE=aws-profile' in profile['Command']

    case = '''
        [profile aws-profile]
        source_profile = source-profile
        [profile source-profile]
    '''
    aws_profiles = create_aws_profiles(create_config(case), azure_path)

    config = cluster_config('foo')
    profile = create_k8s_profile(config, '/dev/null', aws_profiles)
    assert 'AWS_PROFILE=aws-profile' in profile['Command']
    assert 'login-source-profile' == profile['Keyboard Map']['0x61-0x80000']['Text']


def cluster_config(name, aws_profile='aws-profile'):
    return yaml.safe_load(
        'apiVersion: v1\n'
        'clusters:\n'
        '- cluster:\n'
        '    certificate-authority-data: certificate-authority-data\n'
        '    server: server\n'
        f'  name: {name}-name\n'
        'contexts:\n'
        '- context:\n'
        f'    cluster: {name}-name\n'
        f'    user: {name}-user\n'
        f'  name: {name}-name\n'
        f'current-context: {name}-name\n'
        'kind: Config\n'
        'preferences: {}\n'
        'users:\n'
        f'- name: {name}-user\n'
        '  user:\n'
        '    exec:\n'
        '      apiVersion: client.authentication.k8s.io/v1alpha1\n'
        '      args:\n'
        '      - token\n'
        '      - -i\n'
        '      - data\n'
        '      - -r\n'
        '      - arn:aws:iam::account:role\n'
        '      command: aws-iam-authenticator\n'
        '      env:\n'
        '      - name: AWS_PROFILE\n'
        f'        value: {aws_profile}\n'
    )

def test_find_source_profile():
    cases = [
        [
            'profile',
            [{
                'Name': 'profile',
                'Tags': [
                    'source_profile_spf'
                ],
            }],
            'spf',
        ],
        [
            'nonexistingprofile',
            [],
            None,
        ]
    ]

    for profile, profiles, result in cases:
        assert find_source_profile(profile, profiles) == result

    pass

