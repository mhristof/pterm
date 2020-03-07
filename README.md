# pterm
[![PyPI version](https://badge.fury.io/py/pterm.svg)](https://badge.fury.io/py/pterm)

Generates a bunch of usefull iterm2 dynamic profiles

It will load your ~/.aws/config and will generate all the required profiles
for your aws accounts.

It can handle things like `source_profile` or `aws-azure-login` and it will
automatically export the correct `AWS_PROFILE` env var along with a cool badge
for your session.

But wait, there is more.

This script also talks kubernetes. It will scan your ~/.kube/confing and will
separate it out to multiple files. When you launch a k8s profile, the correct
`KUBECOFNIG` and `AWS_PROFILE` is set, plus you get a nice blue color to make
sure you know you are in a k8s enabled environment.

# Installation

```
pip install pterm
```

# Help

```
pterm -h
```
