#! /usr/bin/env pyteron3

import configparser


def get_aws_profiles(aws_config):
    config = configparser.ConfigParser()
    config.read(aws_config)
    ret = []
    loggin_profiles = {}
    for x in config.sections():
        account_number = None
        role = None
        name = x.split()[1]
        if 'role_arn' in config[x]:
            account_number = config[x]['role_arn'].split(':')[4]
            role = config[x]['role_arn'].split(':')[5]
        if 'source_profile' in config[x]:
            loggin_profiles[config[x]['source_profile']] = name
        ret += [[name, account_number, role]]

    for x in ret:
        log = None
        if x[0] in loggin_profiles.keys():
            log = f'log-{loggin_profiles[x[0]]}'
        x += [log]
    return ret


def create_aws_profiles(aws_config):
    aws_profiles = get_aws_profiles(aws_config)

    profiles = []
    for prof, account, role, loggin_for in aws_profiles:
        new = mkprofile(prof, account, role, loggin_for)
        profiles += [new]
    return profiles


def mkprofile(aws_profile, account=None, role=None, loggin_for=None):
    user = os.getenv("USER")
    ret = create_profile(
        aws_profile,
        cmd=f"/usr/bin/env AWS_PROFILE={aws_profile} /usr/bin/login -fp {user}",
        change_title=False,
    )

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




