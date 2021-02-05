#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('README.md', encoding='utf-8') as readme_file:
    readme = readme_file.read()

with open('HISTORY.md', encoding='utf-8') as history_file:
    history = history_file.read()

tests_require = [
    'pytest',
]

development_requires = [
    'twine',
    'wheel',
]

setup(
    author='Fabio Zadrozny',
    author_email='fabiofz@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description='Simple file watching',
    extras_require={
        'test': tests_require,
        'dev': development_requires + tests_require,
    },
    install_package_data=True,
    install_requires=[],
    license='MIT license',
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    include_package_data=True,
    keywords='fsnotify fsnotify fsnotify',
    name='fsnotify',
    packages=find_packages(include=['fsnotify', 'fsnotify.*']),
    python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*',
    setup_requires=[],
    test_suite='tests',
    tests_require=tests_require,
    url='https://github.com/fabioz/fsnotify',
    version='0.1.1',  # Version here and in fsnotify.__init__.py
    zip_safe=False,
)
