""" -----------------------------------------------------
# TECHNOGIX
# -------------------------------------------------------
# Copyright (c) [2022] Technogix SARL
# All rights reserved
# -------------------------------------------------------
# IT orchestrator module setup file
# -------------------------------------------------------
# Nadège LEMPERIERE, @17 october 2021
# Latest revision: 17 october 2021
# --------------------------------------------------- """

from os import path
from setuptools import setup, find_packages
from re import search

setup(
    name = "orchestrator",
    author = "Nadege LEMPERIERE",
    author_email='contact.technogix@gmail.com',
    url='https://github.com/technogix/it-orchestrator/',
    use_scm_version=True,
    packages=find_packages(),
    include_package_data=True,
    description = ("An orchestrator for infrastructure deployment using terraform, ansible, and custom python functions"),
    license = "MIT",
    keywords = "terraform ansible python iac orchestrator",
    install_requires=[ 'boto3>=1.21.43', 'pykeepass>=4.0.1', 'ipaddress>=1.0.3' ],
    classifiers=[
        'Programming Language :: Python',
        'Intended Audience :: Testers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License'
    ],
)