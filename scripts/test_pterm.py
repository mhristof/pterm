#! /usr/bin/env python3:

import tempfile
from pterm import get_aws_profiles
from pterm import create_aws_profiles


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
            [['1', None, None, None, None]],
        ),
        (
            '''
            [profile 2]
            role_arn = arn:partition:service:region:account:resource
            ''',
            [
                ['2', 'account', 'resource', None, None]
            ],
        ),
        (
            '''
            [profile 3]

            [profile 4]
            source_profile = 3
            ''',
            [
                ['3', None, None, None, 'log-4'],
                ['4', None, None, '3', None]
            ],
        )
    ]

    for case, result in cases:
        config = get_aws_profiles(create_config(case))
        assert result == config


def test_create_aws_profiles():
    cases = [
        (
            '''
            [profile 1]
            '''
        ),
    ]
    for case in cases:
        _ = create_aws_profiles(create_config(case))
