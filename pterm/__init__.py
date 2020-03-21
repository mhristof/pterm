#! /usr/bin/env pyteron3

import configparser
import os
from copy import deepcopy
import shutil
import collections
import difflib
import tempfile

has_vault = True
try:
    from sh import vault
except ImportError:
    has_vault = False


def sort_aws_config(path, dry=False):
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


def aws_config_to_profiles(aws_config):
    config = configparser.ConfigParser()
    config.read(aws_config)
    ret = {}
    loggin_profiles = {}
    for x in config.sections():
        new = {
            'name': x.split()[1],
            'account': None,
            'role': None,
            'azure': config[x].get('azure_tenant_id', None) is not None,
            'source_profile': config[x].get('source_profile', None),
        }
        if 'role_arn' in config[x]:
            new['account'] = config[x]['role_arn'].split(':')[4]
            new['role'] = config[x]['role_arn'].split(':')[5]
        ret[new['name']] = new

    return ret


def aws_azure_login_path():
    return which('aws-azure-login')


def which(exe):
    return os.path.dirname(shutil.which(exe))


def create_aws_profiles(aws_config, azure_path=None):
    if azure_path is None:
        azure_path = aws_azure_login_path
    aws_profiles = aws_config_to_profiles(aws_config)

    profiles = []
    login_profile = {}
    for name, profile in aws_profiles.items():
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

    for name, profile in aws_profiles.items():
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
    dictionary['Keyboard Map']["0x61-0x80000"] = {
        "Action": 28,
        "Text": profile,
    }
    return dictionary


def mkprofile(aws_profile, account=None, role=None, source_profile=None, tags=None):
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
    if not has_vault:
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
