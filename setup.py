#! /usr/bin/env python
import setuptools

setuptools.setup(
    name="iterme", # Replace with your own username
    version="0.0.1",
    author="Mike Christof",
    author_email="mhristof@gmail.com",
    description="Setup iterm2",
    long_description="",
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sampleproject",
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    scripts=['scripts/iterme'],
)
