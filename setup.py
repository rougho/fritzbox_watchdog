#!/usr/bin/env python3
"""
Setup script for FritzBox Watchdog
"""

import os
from setuptools import setup, find_packages

# Read the README file
def read_readme():
    try:
        with open("README.md", "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return "FritzBox Router Watchdog - Professional network monitoring solution"


setup(
    name="fritzbox-watchdog",
    version="1.0.0",
    author="rgho",
    description="FritzBox Router Watchdog with TR-064 Protocol Support",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: System Administrators",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Topic :: System :: Networking :: Monitoring",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.6",
    install_requires=[
        # No external dependencies - pure Python standard library
    ],
    entry_points={
        "console_scripts": [
            "fwd=watchdog.main:main",
            "fritzbox-watchdog=watchdog.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
