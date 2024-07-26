# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import os
import random
import re
import semver
from typing import Any, List, TypeVar

from azure.cli.command_modules.acs._client_factory import get_snapshots_client, get_msi_client
from azure.cli.core.azclierror import (
    AzureInternalError,
    AzureResponseError,
    BadRequestError,
    ClientRequestError,
    ForbiddenError,
    InvalidArgumentValueError,
    ResourceNotFoundError,
    ServiceError,
    UnauthorizedError,
    UnclassifiedUserFault,
)
from azure.core.exceptions import AzureError, HttpResponseError, ServiceRequestError, ServiceResponseError
from msrestazure.azure_exceptions import CloudError

# type variables
ManagedCluster = TypeVar("ManagedCluster")


def format_parameter_name_to_option_name(parameter_name: str) -> str:
    """Convert a name in parameter format to option format.

    Underscores ("_") are used to connect the various parts of a parameter name, while hyphens ("-") are used to connect
    each part of an option name. Besides, the option name starts with double hyphens ("--").

    :return: str
    """
    option_name = "--" + parameter_name.replace("_", "-")
    return option_name


def safe_list_get(li: List, idx: int, default: Any = None) -> Any:
    """Get an element from a list without raising IndexError.

    Attempt to get the element with index idx from a list-like object li, and if the index is invalid (such as out of
    range), return default (whose default value is None).

    :return: an element of any type
    """
    if isinstance(li, list):
        try:
            return li[idx]
        except IndexError:
            return default
    return None


def safe_lower(obj: Any) -> Any:
    """Return lowercase string if the provided obj is a string, otherwise return the object itself.

    :return: Any
    """
    if isinstance(obj, str):
        return obj.lower()
    return obj


def get_property_from_dict_or_object(obj, property_name) -> Any:
    """Get the value corresponding to the property name from a dictionary or object.

    Note: Would raise exception if the property does not exist.

    :return: Any
    """
    if isinstance(obj, dict):
        return obj[property_name]
    return getattr(obj, property_name)


def check_is_msi_cluster(mc: ManagedCluster) -> bool:
    """Check `mc` object to determine whether managed identity is enabled.

    :return: bool
    """
    if mc and mc.identity and mc.identity.type is not None:
        identity_type = mc.identity.type.casefold()
        if identity_type in ("systemassigned", "userassigned"):
            return True
    return False


def check_is_private_cluster(mc: ManagedCluster) -> bool:
    """Check `mc` object to determine whether private cluster is enabled.

    :return: bool
    """
    if mc and mc.api_server_access_profile:
        return bool(mc.api_server_access_profile.enable_private_cluster)
    return False


def check_is_apiserver_vnet_integration_cluster(mc: ManagedCluster) -> bool:
    """Check `mc` object to determine whether apiserver vnet integration is enabled.

    Note: enableVnetIntegration is still in preview api so we use additional_properties here

    :return: bool
    """
    if mc and mc.api_server_access_profile:
        additional_properties = mc.api_server_access_profile.additional_properties
        if 'enableVnetIntegration' in additional_properties:
            return additional_properties['enableVnetIntegration']
        return False
    return False


def check_is_private_link_cluster(mc: ManagedCluster) -> bool:
    """Check `mc` object to determine whether private link cluster is enabled.
    :return: bool
    """
    return check_is_private_cluster(mc) and not check_is_apiserver_vnet_integration_cluster(mc)


def check_is_managed_aad_cluster(mc: ManagedCluster) -> bool:
    """Check `mc` object to determine whether managed aad is enabled.

    :return: bool
    """
    if mc and mc.aad_profile is not None and mc.aad_profile.managed:
        return True
    return False


# pylint: disable=too-many-return-statements
def map_azure_error_to_cli_error(azure_error):
    error_message = getattr(azure_error, "message", str(azure_error))
    if isinstance(azure_error, HttpResponseError):
        status_code = getattr(azure_error, "status_code", None)
        if status_code:
            status_code = int(status_code)
            if status_code == 400:
                return BadRequestError(error_message)
            if status_code == 401:
                return UnauthorizedError(error_message)
            if status_code == 403:
                return ForbiddenError(error_message)
            if status_code == 404:
                return ResourceNotFoundError(error_message)
            if 400 <= status_code < 500:
                return UnclassifiedUserFault(error_message)
            if 500 <= status_code < 600:
                return AzureInternalError(error_message)
        return ServiceError(error_message)
    if isinstance(azure_error, ServiceRequestError):
        return ClientRequestError(error_message)
    if isinstance(azure_error, ServiceResponseError):
        return AzureResponseError(error_message)
    return ServiceError(error_message)


def get_snapshot_by_snapshot_id(cli_ctx, snapshot_id):
    _re_snapshot_resource_id = re.compile(
        r"/subscriptions/(.*?)/resourcegroups/(.*?)/providers/microsoft.containerservice/snapshots/(.*)",
        flags=re.IGNORECASE,
    )
    snapshot_id = snapshot_id.lower()
    match = _re_snapshot_resource_id.search(snapshot_id)
    if match:
        subscription_id = match.group(1)
        resource_group_name = match.group(2)
        snapshot_name = match.group(3)
        return get_snapshot(cli_ctx, subscription_id, resource_group_name, snapshot_name)
    raise InvalidArgumentValueError("Cannot parse snapshot name from provided resource id '{}'.".format(snapshot_id))


def get_snapshot(cli_ctx, subscription_id, resource_group_name, snapshot_name):
    snapshot_client = get_snapshots_client(cli_ctx, subscription_id=subscription_id)
    try:
        snapshot = snapshot_client.get(resource_group_name, snapshot_name)
    # track 2 sdk raise exception from azure.core.exceptions
    except AzureError as ex:
        if "not found" in ex.message:
            raise ResourceNotFoundError("Snapshot '{}' not found.".format(snapshot_name))
        raise map_azure_error_to_cli_error(ex)
    return snapshot


def get_user_assigned_identity_by_resource_id(cli_ctx, resource_id):
    _re_user_assigned_identity_resource_id = re.compile(
        r"/subscriptions/(.*?)/resourcegroups/(.*?)/providers/microsoft.managedidentity/userassignedidentities/(.*)",
        flags=re.IGNORECASE,
    )
    resource_id = resource_id.lower()
    match = _re_user_assigned_identity_resource_id.search(resource_id)
    if match:
        subscription_id = match.group(1)
        resource_group_name = match.group(2)
        identity_name = match.group(3)
        return get_user_assigned_identity(cli_ctx, subscription_id, resource_group_name, identity_name)
    raise InvalidArgumentValueError("Cannot parse identity name from provided resource id '{}'.".format(resource_id))


def get_user_assigned_identity(cli_ctx, subscription_id, resource_group_name, identity_name):
    msi_client = get_msi_client(cli_ctx, subscription_id)
    try:
        identity = msi_client.user_assigned_identities.get(
            resource_group_name=resource_group_name, resource_name=identity_name
        )
    # track 1 sdk raise exception from msrestazure.azure_exceptions
    except CloudError as ex:
        if "was not found" in ex.message:
            raise ResourceNotFoundError("Identity '{}' not found.".format(identity_name))
        raise ServiceError(ex.message)
    return identity


def sort_asm_revisions(revisions):
    def _convert_revision_to_semver(rev):
        sr = rev.replace("asm-", "")
        sv = sr.replace("-", ".", 1)
        # Add a custom patch version of 0
        sv += ".0"
        return semver.VersionInfo.parse(sv)

    sorted_revisions = sorted(revisions, key=_convert_revision_to_semver)
    return sorted_revisions


def _get_test_sp_client_id() -> str:
    return os.getenv("AZURE_CLI_TEST_DEV_SP_CLIENT_ID")


def _get_test_sp_object_id(sp_client_id: str) -> str:
    if sp_client_id.replace("-", "").lower() == _get_test_sp_client_id().replace("-", "").lower():
        return os.getenv("AZURE_CLI_TEST_DEV_SP_OBJECT_ID")
    return None


def use_shared_identity() -> bool:
    return os.getenv("USE_SHARED_IDENTITY")


def _get_shared_identity(
    identity_template: str,
    identity_prefix: str,
    identity_max_id: str,
    identity_id: int = 0,
    designated_identity: str = None,
    excluded_identity: str = None,
):
    if designated_identity:
        return designated_identity

    identity = None
    if identity_template and identity_prefix:
        if identity_id:
            identity = identity_template.format(identity_prefix, str(identity_id))
        elif identity_max_id:
            tries = 0
            while tries < 10:
                try:
                    max_id = int(identity_max_id)
                    random_id = random.randint(0, max_id - 2)
                except ValueError:
                    return None
                identity = identity_template.format(identity_prefix, random_id)
                if excluded_identity and identity == excluded_identity:
                    tries += 1
                    continue
                break
    return identity


def get_shared_control_plane_identity(
    designated_identity: str = None, excluded_identity: str = None
) -> str:
    return _get_shared_identity(
        os.getenv("SHARED_CP_IDENTITY_TEMPLATE"),
        os.getenv("SHARED_CP_IDENTITY_PREFIX"),
        os.getenv("SHARED_CP_IDENTITY_MAX_ID"),
        identity_id=0,
        designated_identity=designated_identity,
        excluded_identity=excluded_identity,
    )


def get_shared_kubelet_identity(
    designated_identity: str = None,
    excluded_identity: str = None,
    shared_control_plane_identity: str = None,
    index_shift: int = 0,
) -> str:
    return _get_shared_identity(
        os.getenv("SHARED_KUBELET_IDENTITY_TEMPLATE"),
        os.getenv("SHARED_KUBELET_IDENTITY_PREFIX"),
        os.getenv("SHARED_KUBELET_IDENTITY_MAX_ID"),
        identity_id=_get_id_from_shared_control_plane_identity(
            shared_control_plane_identity
        ) + index_shift,
        designated_identity=designated_identity,
        excluded_identity=excluded_identity,
    )


def _get_id_from_shared_control_plane_identity(shared_identity) -> int:
    if (
        os.getenv("SHARED_CP_IDENTITY_TEMPLATE") and
        os.getenv("SHARED_CP_IDENTITY_PREFIX") and
        shared_identity
    ):
        return int(
            shared_identity.replace(
                os.getenv("SHARED_CP_IDENTITY_TEMPLATE").format(
                    os.getenv("SHARED_CP_IDENTITY_PREFIX"), ""
                ),
                "",
            )
        )
    return 0
