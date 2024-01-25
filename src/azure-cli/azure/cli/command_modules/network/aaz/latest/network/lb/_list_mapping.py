# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
#
# Code generated by aaz-dev-tools
# --------------------------------------------------------------------------------------------

# pylint: skip-file
# flake8: noqa

from azure.cli.core.aaz import *


class ListMapping(AAZCommand):
    """List of inbound NAT rule port mappings.

    :example: List inbound NAT rule port mappings based on IP.
        az network lb list-mapping -n MyLb -g MyResourceGroup --backend-pool-name MyAddressPool --request ip=XX

    :example: List inbound NAT rule port mappings based on NIC.
        az network lb list-mapping -n MyLb -g MyResourceGroup --backend-pool-name MyAddressPool --request nic=XX
    """

    _aaz_info = {
        "version": "2023-09-01",
        "resources": [
            ["mgmt-plane", "/subscriptions/{}/resourcegroups/{}/providers/microsoft.network/loadbalancers/{}/backendaddresspools/{}/queryinboundnatruleportmapping", "2023-09-01"],
        ]
    }

    AZ_SUPPORT_NO_WAIT = True

    def _handler(self, command_args):
        super()._handler(command_args)
        return self.build_lro_poller(self._execute_operations, self._output)

    _args_schema = None

    @classmethod
    def _build_arguments_schema(cls, *args, **kwargs):
        if cls._args_schema is not None:
            return cls._args_schema
        cls._args_schema = super()._build_arguments_schema(*args, **kwargs)

        # define Arg Group ""

        _args_schema = cls._args_schema
        _args_schema.backend_pool_name = AAZStrArg(
            options=["--backend-pool-name"],
            help="The name of the backend address pool.",
            required=True,
            id_part="child_name_1",
        )
        _args_schema.name = AAZStrArg(
            options=["-n", "--name"],
            help="The load balancer name.",
            required=True,
            id_part="name",
        )
        _args_schema.resource_group = AAZResourceGroupNameArg(
            required=True,
        )

        # define Arg Group "Parameters"

        _args_schema = cls._args_schema
        _args_schema.ip_address = AAZStrArg(
            options=["--ip-address"],
            arg_group="Parameters",
            help="IP address set in load balancer backend address.",
        )
        _args_schema.ip_configuration = AAZObjectArg(
            options=["--ip-configuration"],
            arg_group="Parameters",
            help="NetworkInterfaceIPConfiguration set in load balancer backend address.",
        )

        ip_configuration = cls._args_schema.ip_configuration
        ip_configuration.id = AAZStrArg(
            options=["id"],
            help="Resource ID.",
        )
        return cls._args_schema

    def _execute_operations(self):
        self.pre_operations()
        yield self.LoadBalancersListInboundNatRulePortMappings(ctx=self.ctx)()
        self.post_operations()

    @register_callback
    def pre_operations(self):
        pass

    @register_callback
    def post_operations(self):
        pass

    def _output(self, *args, **kwargs):
        result = self.deserialize_output(self.ctx.vars.instance, client_flatten=True)
        return result

    class LoadBalancersListInboundNatRulePortMappings(AAZHttpOperation):
        CLIENT_TYPE = "MgmtClient"

        def __call__(self, *args, **kwargs):
            request = self.make_request()
            session = self.client.send_request(request=request, stream=False, **kwargs)
            if session.http_response.status_code in [202]:
                return self.client.build_lro_polling(
                    self.ctx.args.no_wait,
                    session,
                    self.on_200,
                    self.on_error,
                    lro_options={"final-state-via": "location"},
                    path_format_arguments=self.url_parameters,
                )
            if session.http_response.status_code in [200]:
                return self.client.build_lro_polling(
                    self.ctx.args.no_wait,
                    session,
                    self.on_200,
                    self.on_error,
                    lro_options={"final-state-via": "location"},
                    path_format_arguments=self.url_parameters,
                )

            return self.on_error(session.http_response)

        @property
        def url(self):
            return self.client.format_url(
                "/subscriptions/{subscriptionId}/resourceGroups/{groupName}/providers/Microsoft.Network/loadBalancers/{loadBalancerName}/backendAddressPools/{backendPoolName}/queryInboundNatRulePortMapping",
                **self.url_parameters
            )

        @property
        def method(self):
            return "POST"

        @property
        def error_format(self):
            return "ODataV4Format"

        @property
        def url_parameters(self):
            parameters = {
                **self.serialize_url_param(
                    "backendPoolName", self.ctx.args.backend_pool_name,
                    required=True,
                ),
                **self.serialize_url_param(
                    "groupName", self.ctx.args.resource_group,
                    required=True,
                ),
                **self.serialize_url_param(
                    "loadBalancerName", self.ctx.args.name,
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
                    "Content-Type", "application/json",
                ),
                **self.serialize_header_param(
                    "Accept", "application/json",
                ),
            }
            return parameters

        @property
        def content(self):
            _content_value, _builder = self.new_content_builder(
                self.ctx.args,
                typ=AAZObjectType,
                typ_kwargs={"flags": {"required": True, "client_flatten": True}}
            )
            _builder.set_prop("ipAddress", AAZStrType, ".ip_address")
            _builder.set_prop("ipConfiguration", AAZObjectType, ".ip_configuration")

            ip_configuration = _builder.get(".ipConfiguration")
            if ip_configuration is not None:
                ip_configuration.set_prop("id", AAZStrType, ".id")

            return self.serialize_content(_content_value)

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
            _ListMappingHelper._build_schema_backend_address_inbound_nat_rule_port_mappings_read(cls._schema_on_200)

            return cls._schema_on_200


class _ListMappingHelper:
    """Helper class for ListMapping"""

    _schema_backend_address_inbound_nat_rule_port_mappings_read = None

    @classmethod
    def _build_schema_backend_address_inbound_nat_rule_port_mappings_read(cls, _schema):
        if cls._schema_backend_address_inbound_nat_rule_port_mappings_read is not None:
            _schema.inbound_nat_rule_port_mappings = cls._schema_backend_address_inbound_nat_rule_port_mappings_read.inbound_nat_rule_port_mappings
            return

        cls._schema_backend_address_inbound_nat_rule_port_mappings_read = _schema_backend_address_inbound_nat_rule_port_mappings_read = AAZObjectType()

        backend_address_inbound_nat_rule_port_mappings_read = _schema_backend_address_inbound_nat_rule_port_mappings_read
        backend_address_inbound_nat_rule_port_mappings_read.inbound_nat_rule_port_mappings = AAZListType(
            serialized_name="inboundNatRulePortMappings",
        )

        inbound_nat_rule_port_mappings = _schema_backend_address_inbound_nat_rule_port_mappings_read.inbound_nat_rule_port_mappings
        inbound_nat_rule_port_mappings.Element = AAZObjectType()

        _element = _schema_backend_address_inbound_nat_rule_port_mappings_read.inbound_nat_rule_port_mappings.Element
        _element.backend_port = AAZIntType(
            serialized_name="backendPort",
            flags={"read_only": True},
        )
        _element.frontend_port = AAZIntType(
            serialized_name="frontendPort",
            flags={"read_only": True},
        )
        _element.inbound_nat_rule_name = AAZStrType(
            serialized_name="inboundNatRuleName",
            flags={"read_only": True},
        )
        _element.protocol = AAZStrType()

        _schema.inbound_nat_rule_port_mappings = cls._schema_backend_address_inbound_nat_rule_port_mappings_read.inbound_nat_rule_port_mappings


__all__ = ["ListMapping"]
