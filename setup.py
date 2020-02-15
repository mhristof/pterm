#! /usr/bin/env python
import setuptools

setuptools.setup(
    name="pterm",
    version=tuple(open('version.txt', 'r'))[0],
    author="Mike Christof",
    author_email="mhristof@gmail.com",
    description="Setup iterm2",
    long_description="",
    long_description_content_type="text/markdown",
    url="https://github.com/mhristof/pterm",
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    scripts=['scripts/pterm'],
    install_requires=tuple(open('requirements.txt', 'r')),
)
