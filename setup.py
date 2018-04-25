#!/usr/bin/env python

from setuptools import setup
import sys

__VERSION__ = '0.0.5'

assert sys.version_info[0] == 3, "We require Python > 3"

setup(
    name='bos-mint',
    version=__VERSION__,
    description=(
        'Manual intervention module for PeerPlays'
    ),
    long_description=open('README.md').read(),
    download_url='https://github.com/pbsa/bos-mint/tarball/' + __VERSION__,
    author='Blockchain BV',
    author_email='info@blockchainbv.com',
    maintainer='Fabian Schuh',
    maintainer_email='Fabian.Schuh@BlockchainProjectsBV.com',
    url='http://pbsa.info',
    keywords=['peerplays', 'bos'],
    packages=[
        "bos_mint"
    ],
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
    ],
    entry_points={
        'console_scripts': [
            'bos-mint = bos_mint.cli:main',
        ],
    },
    install_requires=[
        open("requirements.txt").readlines()
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    include_package_data=True,
)
