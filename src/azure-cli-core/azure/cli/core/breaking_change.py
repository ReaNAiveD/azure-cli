# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import abc
import enum
import re

import packaging.version

import requests

from azure.cli.core import __version__

# pylint: disable=protected-access

NEXT_BREAKING_CHANGE_RELEASE = '2.61.0'


def _next_breaking_change_version_from_milestone(cur_version):
    owner = "Azure"
    repo = "azure-cli"
    # The GitHub API v3 URL for milestones
    url = f"https://api.github.com/repos/{owner}/{repo}/milestones"
    try:
        response = requests.get(url)
        response.raise_for_status()
        milestones = response.json()
    except requests.RequestException as e:
        return None
    for milestone in milestones:
        try:
            if 'breaking change' in milestone['title'].lower():
                pattern = re.compile(r'Azure CLI version: *(?P<version>[\d.]+) *$', re.MULTILINE | re.IGNORECASE)
                match = re.search(pattern, milestone['description'])
                if match:
                    version = match.group('version')
                    parsed_version = packaging.version.parse(version)
                    if parsed_version > cur_version:
                        return version
        except (IndexError, KeyError) as e:
            pass
    return None


__bc_version = None


def _next_breaking_change_version():
    global __bc_version
    if __bc_version:
        return __bc_version
    cur_version = packaging.version.parse(__version__)
    next_bc_version = packaging.version.parse(NEXT_BREAKING_CHANGE_RELEASE)
    if cur_version >= next_bc_version:
        fetched_bc_version = _next_breaking_change_version_from_milestone(cur_version)
        if fetched_bc_version:
            __bc_version = fetched_bc_version
            return fetched_bc_version
    __bc_version = NEXT_BREAKING_CHANGE_RELEASE
    return NEXT_BREAKING_CHANGE_RELEASE


class TargetVersionType(int, enum.Enum):
    NextBreakingChangeWindow = 0
    ExactVersion = 1
    Unspecified = 4


class TargetVersion(abc.ABC):
    @abc.abstractmethod
    def __str__(self):
        raise NotImplementedError()


class NextBreakingChangeWindow(TargetVersion):
    version_type = TargetVersionType.NextBreakingChangeWindow

    def __str__(self):
        return f'in next breaking change release({_next_breaking_change_version()})'


class ExactVersion(TargetVersion):
    version_type = TargetVersionType.ExactVersion

    def __init__(self, version):
        self.version = version

    def __str__(self):
        return f'in {self.version}'


class UnspecificVersion(TargetVersion):
    version_type = TargetVersionType.Unspecified

    def __str__(self):
        return 'in future'


class BreakingChangeType(str, enum.Enum):
    Deprecate = 'Deprecate'
    Remove = 'Remove'
    Rename = 'Rename'
    OutputChange = 'Change Output'
    LogicUpdate = 'Update Logic'
    DefaultChange = 'Change Default Value'
    BeRequired = 'Being Required'
    Other = 'Other'


class BreakingChange:
    """

    """
    def __init__(self, command, desc, target_version: TargetVersion = NextBreakingChangeWindow(),
                 bc_type=BreakingChangeType.Other, alter_solution=None, doc_link=None):
        self.command = command
        self.desc = desc
        if isinstance(target_version, str):
            target_version = ExactVersion(target_version)
        self.target_version = target_version
        self.typ = bc_type
        self.alter = alter_solution
        self.doc_link = doc_link

    def __str__(self):
        alter = f' Please use {self.alter} instead.' if self.alter else ''
        link = f' To know more about the Breaking Change, please visit {self.doc_link}.' if self.doc_link else ''
        return f'Upcoming Breaking Change: {self.desc} {self.target_version}.{alter}{link}'

    def pre_announce(self, logger):
        logger.warning(str(self))


upcoming_breaking_changes = {}
