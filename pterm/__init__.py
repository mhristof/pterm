#! /usr/bin/env python3

"""Generate iterm2 profiles for your aws and k8s clusters."""

import sys
import configparser
import os
import re
import json
from copy import deepcopy
import shutil
import collections
import difflib
import tempfile
import boto3
import sh

HAS_SECURITY = True
try:
    from sh import security  # pylint: disable=no-name-in-module
except ImportError:
    HAS_SECURITY = False

HAS_VAULT = True
try:
    from sh import vault
except ImportError:
    HAS_VAULT = False


def sort_aws_config(path, dry=False):
    """Sort the aws config alphabetically."""
    config = configparser.ConfigParser({}, collections.OrderedDict)
    config.read(path)

    for section in config._sections:
        config._sections[section] = collections.OrderedDict(
            sorted(config._sections[section].items(), key=lambda t: t[0])
        )

    # Order all sections alphabetically
    config._sections = collections.OrderedDict(
        sorted(config._sections.items(), key=lambda t: t[0])
    )

    if dry:
        new_config = tempfile.NamedTemporaryFile()
        with open(new_config.name, 'w') as out:
            config.write(out)
        diff = difflib.unified_diff(
            [x.strip() for x in tuple(open(path, 'r'))],
            [x.strip() for x in tuple(open(new_config.name, 'r'))]
        )
        print('\n'.join(diff))
        return
    with open(path, 'w') as out:
        config.write(out)


def dissasemble_iam_arn(arn):
    account = arn.split(':')[4]
    role = arn.split(':')[5]
    return account, role


def aws_config_to_profiles(aws_config):
    """Convert aws config to iterm2 profiles."""
    config = configparser.ConfigParser()
    config.read(aws_config)
    ret = {}
    for section in config.sections():
        new = {
            'name': section.split()[1],
            'account': None,
            'role': None,
            'azure': config[section].get('azure_tenant_id', None) is not None,
            'source_profile': config[section].get('source_profile', None),
        }
        if config[section].get('role_arn', None) is not None:
            new['account'], new['role'] = dissasemble_iam_arn(
                config[section]['role_arn']
            )
        ret[new['name']] = new

    return ret


def aws_azure_login_path():
    """Return the path for aws_azure_login executabl."""
    return which('aws-azure-login')


def which(exe):
    """Return the path for a binary."""
    return os.path.dirname(shutil.which(exe))


def create_aws_profiles(aws_config, azure_path=None):
    """Create aws profiles from a config."""
    if azure_path is None:
        azure_path = aws_azure_login_path
    aws_profiles = aws_config_to_profiles(aws_config)

    profiles = []
    for _, profile in aws_profiles.items():
        new = mkprofile(
            profile['name'],
            source_profile=profile['source_profile'],
            tags=[
                profile['account'],
                profile['role'],
                profile['source_profile']
            ],
        )
        profiles += [new]

    for _, profile in aws_profiles.items():
        source_profile = profile.get("source_profile", None)
        if source_profile is None:
            continue
        new = mkprofile(
            f'login-{source_profile}'
        )
        envs = [f'AWS_PROFILE={source_profile}']
        if aws_profiles[source_profile].get('azure', False):
            path = azure_path()
            envs += [f'PATH={path}']
        node_env = os.getenv('NODE_EXTRA_CA_CERTS', None)
        if node_env is not None:
            envs += [f"NODE_EXTRA_CA_CERTS={node_env}"]
        new["Command"] = f"bash -c '{' '.join(envs)} aws-azure-login --no-prompt || sleep 60'"
        profiles += [new]
    return profiles


def alt_a_split_profile(dictionary, profile):
    """Create the split profile."""
    dictionary['Keyboard Map']["0x61-0x80000"] = {
        "Action": 28,
        "Text": profile,
    }
    return dictionary


def mkprofile(aws_profile, account=None, role=None, source_profile=None, tags=None):
    """Return a new profile."""
    user = os.getenv("USER")
    ret = create_profile(
        aws_profile,
        cmd=f"/usr/bin/env AWS_PROFILE={aws_profile} /usr/bin/login -fp {user}",
        change_title=False,
    )

    if source_profile is not None:
        alt_a_split_profile(ret, f'login-{source_profile}')
        ret['Tags'] += [f'source_profile_{source_profile}']

    if account is not None:
        ret['Tags'] += [account]
    if role is not None:
        ret['Tags'] += [role]
    if tags is not None:
        ret['Tags'] += [x for x in tags if x]

    if 'prod' in aws_profile and 'nonprod' not in aws_profile:
        ret["Background Color"] = {
            "Red Component": 0.217376708984375,
            "Color Space": "sRGB",
            "Blue Component": 0,
            "Alpha Component": 1,
            "Green Component": 0
        }

    return ret


def create_profile(name, cmd=None, change_title=False, tags=None, badge=True):
    """Create a new profile."""
    if tags is None:
        tags = []

    ret = {
        "Name": name,
        "Guid": name,
        "Unlimited Scrollback": True,
        "Title Components": 32,
        "Custom Window Title": name,
        "Allow Title Setting": change_title,
        "Tags": tags,
        "Smart Selection Rules": smart_selection_rules(),
        "Custom Directory": "Recycle",
        "Flashing Bell": True,
        "Silence Bell": True,
        "Triggers": triggers(),
        "Keyboard Map": keybinds(),
    }

    if badge:
        ret["Badge Text"] = name

    if cmd is not None:
        ret["Command"] = cmd
        ret["Custom Command"] = "Yes"
    return ret


def keybinds():
    """Return the dictionary for keybinds."""
    return {
        # cmd + shift + -
        "0x5f-0x120000": {
            "Action": 25,
            "Text": "Split Horizontally with Current Profile\nSplit Horizontally with Current Profile"
        },
        # cmd + shift + \
        "0x7c-0x120000": {
            "Action": 25,
            "Text": "Split Vertically with Current Profile\nSplit Vertically with Current Profile"
        },
    }


def triggers():
    """Return the triggers for profiles."""
    return [
        {
            "partial": True,
            "parameter": "id_rsa",
            "regex": f"^Enter passphrase for (key ')?{os.getenv('HOME')}/.ssh/id_rsa",
            "action": "PasswordTrigger"
        },
        {
            "action": "PasswordTrigger",
            "parameter": "macos",
            "regex": "^Password: .input is hidden.",
            "partial": True
        }
    ]


def smart_selection_rules():
    """Return the smart selection roles for the profiles."""
    return [
        {
            "notes": "terraform aws resource",
            "precision": "normal",
            "regex": "resource \"aws_([a-zA-Z_]*)\"",
            "actions": [
                {
                    "title": "open webpage",
                    "action": 1,
                    "parameter": r"https://www.terraform.io/docs/providers/aws/r/\1.html"
                }
            ]
        },
        {
            "notes": "terraform aws data",
            "precision": "normal",
            "regex": "data \"aws_([a-zA-Z_]*)\"",
            "actions": [
                {
                    "title": "open webpage",
                    "action": 1,
                    "parameter": r"https://www.terraform.io/docs/providers/aws/d/\1.html"
                }
            ]
        },
        {
            "notes": "aws acm-pca",
            "precision": "normal",
            "regex": "arn:aws:acm-pca:([\w-]*):(\d*):certificate-authority/([\w-]*)",
            "actions": [
                {
                    "title": "open webpage",
                    "action": 1,
                    "parameter": r"https://\1.console.aws.amazon.com/acm-pca/home?region=\1#/certificateAuthorities?arn=arn:aws:acm-pca:\1:\2:certificate-authority~2F\3",
                }
            ]
        },
        {
            "notes": "aws iam-policy",
            "precision": "normal",
            "regex": "arn:aws:iam::(\d*):policy/([\w-]*)",
            "actions": [
                {
                    "title": "open webpage",
                    "action": 1,
                    "parameter": r"https://console.aws.amazon.com/iam/home?#/policies/arn:aws:iam::\1:policy/\2$serviceLevelSummary",
                }
            ]
        },
        {
            "notes": "aws iam-role",
            "precision": "normal",
            "regex": "arn:aws:iam::\d*:role/([\w-_]*)",
            "actions": [
                {
                    "title": "open webpage",
                    "action": 1,
                    "parameter": r"https://console.aws.amazon.com/iam/home?#/roles/\1"
                }
            ]
        },
        {
            "notes": "aws lambda",
            "precision": "normal",
            "regex": "arn:aws:lambda:([\w-]*):\d*:function:([\w-_]*)",
            "actions": [
                {
                    "title": "open webpage",
                    "action": 1,
                    "parameter": r"https://\1.console.aws.amazon.com/lambda/home?region=\1#/functions/\2?tab=configuration",
                }
            ]
        },
    ]


def create_k8s_profile(this, cfg, aws_profiles):
    """Create a kubernetes profile."""
    user = os.getenv("USER")
    aws_profile = None
    cluster = this['current-context']
    cmd = [
        "/usr/bin/env",
        f"KUBECONFIG={cfg}",
    ]
    try:
        env = this['users'][0]['user']['exec']['env'][0]
        if env['name'] != 'AWS_PROFILE':
            pass
        aws_profile = env['value']
    except KeyError:
        pass
    except TypeError:
        pass
    except IndexError:
        pass

    if aws_profile is not None:
        cmd += [f'AWS_PROFILE={aws_profile}']

    cmd += [
        '/usr/bin/login',
        '-fp',
        f'{user}',
    ]

    new = create_profile(
        f'k8s-{cluster}',
        cmd=' '.join(cmd),
        change_title=False,
        tags=['k8s'],
    )

    source_profile = find_source_profile(aws_profile, aws_profiles)
    if source_profile is not None:
        new = alt_a_split_profile(new, f'login-{source_profile}')

    new["Background Color"] = {
        "Red Component": 0,
        "Color Space": "sRGB",
        "Blue Component": 0.38311767578125,
        "Alpha Component": 1,
        "Green Component": 0
    }
    return new


def find_source_profile(profile, aws_profiles):
    """Retrieve the source profile for a profile."""
    this_aws_profile = [
        x for x in aws_profiles
        if x.get('Name') == profile
    ]
    try:
        this_aws_profile = this_aws_profile[0]
    except IndexError:
        print(f"Error, profile ${profile} not found in aws config")
        return None

    return [
        x.replace('source_profile_', '')
        for x in this_aws_profile['Tags']
        if x is not None and x.startswith('source_profile_')
    ][0]


def create_vault_profile(name):
    """Create a vault profile."""
    if not HAS_VAULT:
        return {}
    new = create_profile(
        name,
        change_title=False,
        badge=True,
        cmd=f"/bin/bash -c 'PATH={which('vault')} vault server -dev'",
        tags=vault(
            '--version', _env={'VAULT_CLI_NO_COLOR': "true"}
        ).strip().split()
    )
    new['Triggers'] = [
        {
            "action": "CoprocessTrigger",
            "parameter": r"/bin/bash -c 'echo \1 > ~/.vault-token'",
            "regex": r"Root Token: (s\..*)",
            "partial": True
        }
    ]

    new['Keyboard Map'] = {
        "0x77-0x100000": {
            "Action": 12,
            "Text": "Control-w is disabled, please use Control-c to close this tab"
        }
    }

    return new


def get_keys_from_file(csv):
    """Extract the credentials from a csv file."""
    lines = tuple(open(csv, 'r'))
    creds = lines[1]
    access = creds.split(',')[2]
    secret = creds.split(',')[3]
    return access, secret


def cache():
    return 'pterm-iam-list'

def generate_key_profiles(creds, keychain):
    """Create the AWS profiles from credentials the user has stored."""
    ret = []

    if creds is not None:
        profile_from_creds(creds, keychain, cache())

    arns = security_find(cache())

    for arn in json.loads(arns):
        ret += [profile_from_arn(arn)]

    return ret


def profile_from_creds(creds, keychain, cache):
    """Create a profile from an AWS credentials file."""
    access_key, secret_key = get_keys_from_file(creds)

    arn = security_store(access_key, secret_key, keychain, cache)
    return profile_from_arn(arn)


def profile_from_arn(arn):
    """Create a profile from an ARN."""
    tags = list(dissasemble_iam_arn(arn))

    _, key, _, secret = re.split("[ =]", security_find(arn))
    alias = account_aliases(key, secret)
    if alias != '':
        tags += [alias]

    user = os.getenv("USER")
    ret = create_profile(
        arn,
        cmd="/bin/false",
        change_title=False,
        tags=tags,
    )
    ret['Initial Text'] = f'export $(security find-generic-password -a {user} -s {arn} -w)'
    ret["Custom Command"] = "No"

    return ret


def aws_key_name(access_key, secret_key):
    """Retrieve the arn of the given key."""
    client = boto3.client(
        'sts',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    response = client.get_caller_identity()
    return response['Arn']


def security_find(name):
    """Find a macOS keychain item with given name.

    Returns None if nothing is found.
    """
    try:
        return str(security(
            'find-generic-password',
            '-a', os.getenv("USER"),
            '-s', name,
            '-w'
        )).rstrip()
    except sh.ErrorReturnCode_44:  # pylint: disable=no-member
        return None


def account_aliases(access_key, secret_key):
    """Find an AWS account alias."""
    client = boto3.client(
        'iam',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    paginator = client.get_paginator('list_account_aliases')
    for response in paginator.paginate():
        try:
            return response['AccountAliases'][0]
        except (IndexError, KeyError) as _:
            pass
    return ''


def security_store(access_key, secret_key, keychain, cache):
    """Store the AWS credentials in the macOS keychain.

    An entry is also added in the cache keychain entry, see
    security_add_to_list.
    """
    name = aws_key_name(access_key, secret_key)
    data = f"AWS_ACCESS_KEY_ID={access_key} AWS_SECRET_KEY_ID={secret_key}"
    existing_key = security_find(name)

    if existing_key == data:
        return name

    security(
        'add-generic-password',
        '-a', os.getenv("USER"),
        '-s', name,
        '-w', data,
        keychain
    )

    security_add_to_list(name, keychain, cache)

    return name


def security_add_to_list(name, keychain, cache):
    """Add a key in the keychain cache.

    MacOS doesnt allow to list all the secrets so a list is maintaind for
    pterm to allow adding all profiles that were created via cmd line
    """
    data = security_find(cache)

    if data is not None:
        security(
            'delete-generic-password', '-a', os.getenv("USER"), '-s', cache
        )
        data = json.loads(data)
    else:
        data = []

    data += [name]

    security(
        'add-generic-password',
        '-a', os.getenv("USER"),
        '-s', cache,
        '-w', json.dumps(data),
        keychain
    )

    return data
