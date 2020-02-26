#! /usr/bin/env pyteron3

import configparser
import os
from copy import deepcopy
import shutil
import collections
import difflib
import tempfile


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


def get_aws_profiles(aws_config):
    config = configparser.ConfigParser()
    config.read(aws_config)
    ret = []
    loggin_profiles = {}
    for x in config.sections():
        account_number = None
        role = None
        name = x.split()[1]
        source_profile = None
        azure = False
        if 'role_arn' in config[x]:
            account_number = config[x]['role_arn'].split(':')[4]
            role = config[x]['role_arn'].split(':')[5]
        if 'source_profile' in config[x]:
            loggin_profiles[config[x]['source_profile']] = name
            source_profile = config[x]['source_profile']
        if 'azure_tenant_id' in config[x]:
            azure = True
        ret += [[name, account_number, role, source_profile, azure]]

    for x in ret:
        log = None
        if x[0] in loggin_profiles.keys():
            log = f'log-{loggin_profiles[x[0]]}'
        x += [log]
    return ret


def aws_azure_login_path():
    return os.path.dirname(shutil.which('aws-azure-login'))


def create_aws_profiles(aws_config, azure_path=None):
    if azure_path is None:
        azure_path = aws_azure_login_path
    aws_profiles = get_aws_profiles(aws_config)

    profiles = []
    login_profile = {}
    for prof, account, role, source_profile, azure, loggin_for in aws_profiles:
        new = mkprofile(prof, account, role, source_profile, loggin_for)
        if azure:
            new['Tags'] += ['azure']
        profiles += [new]
        if loggin_for is not None:
            new = deepcopy(new)
            name = new['Name']
            new['Name'] = f'login-{name}'
            new['Guid'] = f'login-{name}'
            envs = [f'AWS_PROFILE={prof}']
            if azure:
                path = azure_path()
                envs += [f'PATH={path}']
            node_env = os.getenv('NODE_EXTRA_CA_CERTS', None)
            if node_env is not None:
                envs += [f"NODE_EXTRA_CA_CERTS={node_env}"]
            new["Command"] = f"bash -c '{' '.join(envs)} aws-azure-login --no-prompt || sleep 60'"
            profiles += [new]
    return profiles


def mkprofile(aws_profile, account=None, role=None, source_profile=None, loggin_for=None):
    user = os.getenv("USER")
    ret = create_profile(
        aws_profile,
        cmd=f"/usr/bin/env AWS_PROFILE={aws_profile} /usr/bin/login -fp {user}",
        change_title=False,
    )

    if source_profile is not None:
        # alt + a
        ret['Keyboard Map']["0x61-0x80000"] = {
            "Action": 28,
            "Text": f'login-{source_profile}',
        }

    if account is not None:
        ret['Tags'] += [account]
    if role is not None:
        ret['Tags'] += [role]
    if loggin_for is not None:
        ret['Tags'] += [loggin_for]

    if 'prod' in aws_profile:
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
        "0x5f-0x120000" : {
            "Action" : 25,
            "Text" : "Split Horizontally with Current Profile\nSplit Horizontally with Current Profile"
        },
        # cmd + shift + \
        "0x7c-0x120000" : {
            "Action" : 25,
            "Text" : "Split Vertically with Current Profile\nSplit Vertically with Current Profile"
        },
    }


def triggers():
    return [
        {
            "partial": True,
            "parameter": "id_rsa",
            "regex": f"^Enter passphrase for key {os.getenv('HOME')}/.ssh/id_rsa",
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



