#! /usr/bin/env python
import setuptools
from pterm import version

setuptools.setup(
    name="pterm",
    version=version.__version__,
    author="Mike Christof",
    author_email="mhristof@gmail.com",
    description="Setup iterm2",
    long_description='\n'.join(tuple(open('README.md', 'r'))),
    long_description_content_type="text/markdown",
    url="https://github.com/mhristof/pterm",
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    scripts=['scripts/pterm'],
    install_requires=tuple(open('requirements.txt', 'r')),
)
