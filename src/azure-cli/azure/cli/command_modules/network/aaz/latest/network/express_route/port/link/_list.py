# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
#
# Code generated by aaz-dev-tools
# --------------------------------------------------------------------------------------------

# pylint: skip-file
# flake8: noqa

from azure.cli.core.aaz import *


@register_command(
    "network express-route port link list",
)
class List(AAZCommand):
    """List ExpressRoute links.

    :example: List ExpressRoute links.
        az network express-route port link list --port-name MyPort --resource-group MyResourceGroup
    """

    _aaz_info = {
        "version": "2023-09-01",
        "resources": [
            ["mgmt-plane", "/subscriptions/{}/resourcegroups/{}/providers/microsoft.network/expressrouteports/{}", "2023-09-01", "properties.links"],
        ]
    }

    def _handler(self, command_args):
        super()._handler(command_args)
        self.SubresourceSelector(ctx=self.ctx, name="subresource")
        self._execute_operations()
        return self._output()

    _args_schema = None

    @classmethod
    def _build_arguments_schema(cls, *args, **kwargs):
        if cls._args_schema is not None:
            return cls._args_schema
        cls._args_schema = super()._build_arguments_schema(*args, **kwargs)

        # define Arg Group ""

        _args_schema = cls._args_schema
        _args_schema.port_name = AAZStrArg(
            options=["--port-name"],
            help="ExpressRoute port name.",
            required=True,
        )
        _args_schema.resource_group = AAZResourceGroupNameArg(
            required=True,
        )
        return cls._args_schema

    def _execute_operations(self):
        self.pre_operations()
        self.ExpressRoutePortsGet(ctx=self.ctx)()
        self.post_operations()

    @register_callback
    def pre_operations(self):
        pass

    @register_callback
    def post_operations(self):
        pass

    def _output(self, *args, **kwargs):
        result = self.deserialize_output(self.ctx.selectors.subresource.required(), client_flatten=True)
        return result

    class SubresourceSelector(AAZJsonSelector):

        def _get(self):
            result = self.ctx.vars.instance
            return result.properties.links

        def _set(self, value):
            result = self.ctx.vars.instance
            result.properties.links = value
            return

    class ExpressRoutePortsGet(AAZHttpOperation):
        CLIENT_TYPE = "MgmtClient"

        def __call__(self, *args, **kwargs):
            request = self.make_request()
            session = self.client.send_request(request=request, stream=False, **kwargs)
            if session.http_response.status_code in [200]:
                return self.on_200(session)

            return self.on_error(session.http_response)

        @property
        def url(self):
            return self.client.format_url(
                "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Network/ExpressRoutePorts/{expressRoutePortName}",
                **self.url_parameters
            )

        @property
        def method(self):
            return "GET"

        @property
        def error_format(self):
            return "ODataV4Format"

        @property
        def url_parameters(self):
            parameters = {
                **self.serialize_url_param(
                    "expressRoutePortName", self.ctx.args.port_name,
                    required=True,
                ),
                **self.serialize_url_param(
                    "resourceGroupName", self.ctx.args.resource_group,
                    required=True,
                ),
                **self.serialize_url_param(
                    "subscriptionId", self.ctx.subscription_id,
                    required=True,
                ),
            }
            return parameters

        @property
        def query_parameters(self):
            parameters = {
                **self.serialize_query_param(
                    "api-version", "2023-09-01",
                    required=True,
                ),
            }
            return parameters

        @property
        def header_parameters(self):
            parameters = {
                **self.serialize_header_param(
                    "Accept", "application/json",
                ),
            }
            return parameters

        def on_200(self, session):
            data = self.deserialize_http_content(session)
            self.ctx.set_var(
                "instance",
                data,
                schema_builder=self._build_schema_on_200
            )

        _schema_on_200 = None

        @classmethod
        def _build_schema_on_200(cls):
            if cls._schema_on_200 is not None:
                return cls._schema_on_200

            cls._schema_on_200 = AAZObjectType()
            _ListHelper._build_schema_express_route_port_read(cls._schema_on_200)

            return cls._schema_on_200


class _ListHelper:
    """Helper class for List"""

    _schema_express_route_port_read = None

    @classmethod
    def _build_schema_express_route_port_read(cls, _schema):
        if cls._schema_express_route_port_read is not None:
            _schema.etag = cls._schema_express_route_port_read.etag
            _schema.id = cls._schema_express_route_port_read.id
            _schema.identity = cls._schema_express_route_port_read.identity
            _schema.location = cls._schema_express_route_port_read.location
            _schema.name = cls._schema_express_route_port_read.name
            _schema.properties = cls._schema_express_route_port_read.properties
            _schema.tags = cls._schema_express_route_port_read.tags
            _schema.type = cls._schema_express_route_port_read.type
            return

        cls._schema_express_route_port_read = _schema_express_route_port_read = AAZObjectType()

        express_route_port_read = _schema_express_route_port_read
        express_route_port_read.etag = AAZStrType(
            flags={"read_only": True},
        )
        express_route_port_read.id = AAZStrType()
        express_route_port_read.identity = AAZObjectType()
        express_route_port_read.location = AAZStrType()
        express_route_port_read.name = AAZStrType(
            flags={"read_only": True},
        )
        express_route_port_read.properties = AAZObjectType(
            flags={"client_flatten": True},
        )
        express_route_port_read.tags = AAZDictType()
        express_route_port_read.type = AAZStrType(
            flags={"read_only": True},
        )

        identity = _schema_express_route_port_read.identity
        identity.principal_id = AAZStrType(
            serialized_name="principalId",
            flags={"read_only": True},
        )
        identity.tenant_id = AAZStrType(
            serialized_name="tenantId",
            flags={"read_only": True},
        )
        identity.type = AAZStrType()
        identity.user_assigned_identities = AAZDictType(
            serialized_name="userAssignedIdentities",
        )

        user_assigned_identities = _schema_express_route_port_read.identity.user_assigned_identities
        user_assigned_identities.Element = AAZObjectType()

        _element = _schema_express_route_port_read.identity.user_assigned_identities.Element
        _element.client_id = AAZStrType(
            serialized_name="clientId",
            flags={"read_only": True},
        )
        _element.principal_id = AAZStrType(
            serialized_name="principalId",
            flags={"read_only": True},
        )

        properties = _schema_express_route_port_read.properties
        properties.allocation_date = AAZStrType(
            serialized_name="allocationDate",
            flags={"read_only": True},
        )
        properties.bandwidth_in_gbps = AAZIntType(
            serialized_name="bandwidthInGbps",
        )
        properties.billing_type = AAZStrType(
            serialized_name="billingType",
        )
        properties.circuits = AAZListType(
            flags={"read_only": True},
        )
        properties.encapsulation = AAZStrType()
        properties.ether_type = AAZStrType(
            serialized_name="etherType",
            flags={"read_only": True},
        )
        properties.links = AAZListType()
        properties.mtu = AAZStrType(
            flags={"read_only": True},
        )
        properties.peering_location = AAZStrType(
            serialized_name="peeringLocation",
        )
        properties.provisioned_bandwidth_in_gbps = AAZFloatType(
            serialized_name="provisionedBandwidthInGbps",
            flags={"read_only": True},
        )
        properties.provisioning_state = AAZStrType(
            serialized_name="provisioningState",
            flags={"read_only": True},
        )
        properties.resource_guid = AAZStrType(
            serialized_name="resourceGuid",
            flags={"read_only": True},
        )

        circuits = _schema_express_route_port_read.properties.circuits
        circuits.Element = AAZObjectType()

        _element = _schema_express_route_port_read.properties.circuits.Element
        _element.id = AAZStrType()

        links = _schema_express_route_port_read.properties.links
        links.Element = AAZObjectType()

        _element = _schema_express_route_port_read.properties.links.Element
        _element.etag = AAZStrType(
            flags={"read_only": True},
        )
        _element.id = AAZStrType()
        _element.name = AAZStrType()
        _element.properties = AAZObjectType(
            flags={"client_flatten": True},
        )

        properties = _schema_express_route_port_read.properties.links.Element.properties
        properties.admin_state = AAZStrType(
            serialized_name="adminState",
        )
        properties.colo_location = AAZStrType(
            serialized_name="coloLocation",
            flags={"read_only": True},
        )
        properties.connector_type = AAZStrType(
            serialized_name="connectorType",
            flags={"read_only": True},
        )
        properties.interface_name = AAZStrType(
            serialized_name="interfaceName",
            flags={"read_only": True},
        )
        properties.mac_sec_config = AAZObjectType(
            serialized_name="macSecConfig",
        )
        properties.patch_panel_id = AAZStrType(
            serialized_name="patchPanelId",
            flags={"read_only": True},
        )
        properties.provisioning_state = AAZStrType(
            serialized_name="provisioningState",
            flags={"read_only": True},
        )
        properties.rack_id = AAZStrType(
            serialized_name="rackId",
            flags={"read_only": True},
        )
        properties.router_name = AAZStrType(
            serialized_name="routerName",
            flags={"read_only": True},
        )

        mac_sec_config = _schema_express_route_port_read.properties.links.Element.properties.mac_sec_config
        mac_sec_config.cak_secret_identifier = AAZStrType(
            serialized_name="cakSecretIdentifier",
        )
        mac_sec_config.cipher = AAZStrType()
        mac_sec_config.ckn_secret_identifier = AAZStrType(
            serialized_name="cknSecretIdentifier",
        )
        mac_sec_config.sci_state = AAZStrType(
            serialized_name="sciState",
        )

        tags = _schema_express_route_port_read.tags
        tags.Element = AAZStrType()

        _schema.etag = cls._schema_express_route_port_read.etag
        _schema.id = cls._schema_express_route_port_read.id
        _schema.identity = cls._schema_express_route_port_read.identity
        _schema.location = cls._schema_express_route_port_read.location
        _schema.name = cls._schema_express_route_port_read.name
        _schema.properties = cls._schema_express_route_port_read.properties
        _schema.tags = cls._schema_express_route_port_read.tags
        _schema.type = cls._schema_express_route_port_read.type


__all__ = ["List"]
