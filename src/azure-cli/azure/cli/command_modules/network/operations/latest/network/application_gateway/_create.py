from argcomplete import FilesCompleter
from knack.arguments import CLIArgumentType

from azure.cli.command_modules.network._actions import TrustedClientCertificateCreate, SslProfilesCreate
from azure.cli.command_modules.network._completers import subnet_completion_list
from azure.cli.core import LocalContextAction
from azure.cli.core.commands.parameters import get_resource_name_completion_list, get_location_type, tags_type, \
    get_enum_type, zones_type, get_three_state_flag, file_type
from azure.cli.core.commands.template_create import get_folded_parameter_help_string
from azure.cli.core.commands.validators import get_default_location_from_resource_group
from azure.cli.core.local_context import LocalContextAttribute
from azure.cli.core.util import sdk_no_wait
from azure.cli.core.aaz import register_command
from azure.cli.core.commands import DeploymentOutputLongRunningOperation, OperationCommand
from azure.cli.core.commands.arm import (
    ResourceType, deployment_validate_table_format, handle_template_based_exception)
from azure.cli.core.commands.client_factory import get_subscription_id, get_mgmt_service_client
from azure.cli.command_modules.network._validators import process_ag_create_namespace, validate_private_ip_address, \
    validate_custom_error_pages, validate_waf_policy, validate_user_assigned_identity, get_servers_validator
from azure.mgmt.core.tools import is_valid_resource_id, resource_id
from knack.log import get_logger

logger = get_logger(__name__)


def _log_pprint_template(template):
    import json
    logger.info('==== BEGIN TEMPLATE ====')
    logger.info(json.dumps(template, indent=2))
    logger.info('==== END TEMPLATE ====')


def _is_v2_sku(sku):
    return 'v2' in sku


@register_command(
    "network application-gateway create",
)
class ApplicationGatewayCreate(OperationCommand):
    def __init__(self, loader, **kwargs):
        """
        :param loader: it is required for command registered in the command table
        """
        self.loader = loader
        super().__init__(
            loader=loader,
            name=self.AZ_NAME,
            handler=True,
            transform=DeploymentOutputLongRunningOperation(loader.cli_ctx),
            supports_no_wait=True,
            table_transformer=deployment_validate_table_format,
            validator=process_ag_create_namespace,
            exception_handler=handle_template_based_exception,
            **kwargs
        )

    def load_arguments(self):
        super().load_arguments()
        virtual_network_name_type = CLIArgumentType(options_list='--vnet-name', metavar='NAME', help='The virtual network (VNet) name.', completer=get_resource_name_completion_list('Microsoft.Network/virtualNetworks'),
                                                    local_context_attribute=LocalContextAttribute(name='vnet_name', actions=[LocalContextAction.GET]))
        private_ip_address_type = CLIArgumentType(help='Static private IP address to use.', validator=validate_private_ip_address)
        app_gateway_name_type = CLIArgumentType(help='Name of the application gateway.', options_list='--gateway-name', completer=get_resource_name_completion_list('Microsoft.Network/applicationGateways'), id_part='name')
        ag_servers_type = CLIArgumentType(nargs='+', help='Space-separated list of IP addresses or DNS names corresponding to backend servers.', validator=get_servers_validator())
        cookie_based_affinity_type = CLIArgumentType(arg_type=get_three_state_flag(positive_label='Enabled', negative_label='Disabled', return_label=True))
        http_protocol_type = CLIArgumentType(get_enum_type(["Http", "Https", "Tcp", "Tls"]))

        with self.arguments_context() as arg_ctx:
            arg_ctx.argument('virtual_network_name', virtual_network_name_type, id_part='name')
            arg_ctx.argument('tags', tags_type)
            arg_ctx.argument('private_ip_address', private_ip_address_type)
            arg_ctx.argument('location', get_location_type(self.cli_ctx), validator=get_default_location_from_resource_group)
            arg_ctx.argument('application_gateway_name', app_gateway_name_type, options_list=['--name', '-n'])
            skus = ["Standard_Small", "Standard_Medium", "WAF_Medium", "WAF_Large", "Standard_v2", "WAF_v2"]
            arg_ctx.argument('sku', arg_group='Gateway', help='The name of the SKU.', arg_type=get_enum_type(skus), default="Standard_Medium")
            arg_ctx.argument('min_capacity', help='Lower bound on the number of application gateway instances.', type=int)
            arg_ctx.argument('max_capacity', help='Upper bound on the number of application gateway instances.', type=int)
            arg_ctx.argument('zones', zones_type)
            arg_ctx.argument('custom_error_pages', nargs='+', help='Space-separated list of custom error pages in `STATUS_CODE=URL` format.', validator=validate_custom_error_pages)
            arg_ctx.argument('firewall_policy', options_list='--waf-policy', help='Name or ID of a web application firewall (WAF) policy.', validator=validate_waf_policy)
            arg_ctx.argument('priority', type=int, help='Priority of the request routing rule. Supported SKU tiers are Standard_v2, WAF_v2.')

        with self.arguments_context(arg_group='Identity') as c:
            c.argument('user_assigned_identity', options_list='--identity', help="Name or ID of the ManagedIdentity Resource", validator=validate_user_assigned_identity)

        with self.arguments_context(arg_group='Network') as c:
            c.argument('virtual_network_name', virtual_network_name_type)
            c.argument('private_ip_address')
            c.argument('public_ip_address_allocation', help='The kind of IP allocation to use when creating a new public IP.', default="Dynamic")
            c.argument('subnet_address_prefix', help='The CIDR prefix to use when creating a new subnet.')
            c.argument('vnet_address_prefix', help='The CIDR prefix to use when creating a new VNet.')

        with self.arguments_context(arg_group='Gateway') as c:
            c.argument('servers', ag_servers_type)
            c.argument('capacity', help='The number of instances to use with the application gateway.', type=int)
            c.argument('http_settings_cookie_based_affinity', cookie_based_affinity_type, help='Enable or disable HTTP settings cookie-based affinity.')
            c.argument('http_settings_protocol', http_protocol_type, help='The HTTP settings protocol.')
            c.argument('enable_http2', arg_type=get_three_state_flag(positive_label='Enabled', negative_label='Disabled'), options_list=['--http2'], help='Use HTTP2 for the application gateway.')
            c.ignore('public_ip_address_type')
            c.ignore('subnet_type')
            c.argument('ssl_profile_id', help='SSL profile resource of the application gateway.', is_preview=True)
            c.argument('enable_fips', arg_type=get_three_state_flag(), help='Whether FIPS is enabled on the application gateway resource.')

        with self.arguments_context(arg_group='Private Link Configuration') as c:
            c.argument('enable_private_link',
                       action='store_true',
                       help='Enable Private Link feature for this application gateway. '
                            'If both public IP and private IP are enbaled, taking effect only in public frontend IP',
                       default=False)
            c.argument('private_link_ip_address', help='The static private IP address of a subnet for Private Link. If omitting, a dynamic one will be created')
            c.argument('private_link_subnet_prefix', help='The CIDR prefix to use when creating a new subnet')
            c.argument('private_link_subnet', help='The name of the subnet within the same vnet of an application gateway')
            c.argument('private_link_primary', arg_type=get_three_state_flag(), help='Whether the IP configuration is primary or not')

        with self.arguments_context(arg_group='Mutual Authentication Support') as c:
            c.argument('trusted_client_cert', nargs='+', action=TrustedClientCertificateCreate, is_preview=True)

        with self.arguments_context(arg_group='SSL Profile') as c:
            c.argument('ssl_profile', nargs='+', action=SslProfilesCreate, is_preview=True)

        with self.arguments_context() as c:
            c.argument('validate', help='Generate and validate the ARM template without creating any resources.', action='store_true')
            c.argument('routing_rule_type', arg_group='Gateway', help='The request routing rule type.', arg_type=get_enum_type(["Basic", "PathBasedRouting"]))
            public_ip_help = get_folded_parameter_help_string('public IP address', allow_none=True, allow_new=True, default_none=True)
            c.argument('public_ip_address', help=public_ip_help, completer=get_resource_name_completion_list('Microsoft.Network/publicIPAddresses'), arg_group='Network')
            subnet_help = get_folded_parameter_help_string('subnet', other_required_option='--vnet-name', allow_new=True)
            c.argument('subnet', help=subnet_help, completer=subnet_completion_list, arg_group='Network')
            c.argument('connection_draining_timeout', type=int, help='The time in seconds after a backend server is removed during which on open connection remains active. Range: 0 (disabled) to 3600', arg_group='Gateway')

        with self.arguments_context(arg_group='Gateway') as c:
            c.argument('cert_data', options_list='--cert-file', type=file_type, completer=FilesCompleter(), help='The path to the PFX certificate file.')
            c.argument('frontend_port', help='The front end port number.')
            c.argument('cert_password', help='The certificate password')
            c.argument('http_settings_port', help='The HTTP settings port.')
            c.argument('servers', ag_servers_type)
            c.argument('key_vault_secret_id', help="Secret Id of (base-64 encoded unencrypted pfx) 'Secret' or 'Certificate' object stored in Azure KeyVault. You need enable soft delete for keyvault to use this feature.")
            c.argument('ssl_cert_name', options_list='--ssl-certificate-name', help="The certificate name. Default will be `<application-gateway-name>SslCert`.")

    def handle(self, cmd, application_gateway_name, resource_group_name, location=None,
                tags=None, no_wait=False, capacity=2,
                cert_data=None, cert_password=None, key_vault_secret_id=None,
                frontend_port=None, http_settings_cookie_based_affinity='disabled',
                http_settings_port=80, http_settings_protocol='Http',
                routing_rule_type='Basic', servers=None,
                sku=None, priority=None, private_ip_address=None, public_ip_address=None,
                public_ip_address_allocation=None,
                subnet='default', subnet_address_prefix='10.0.0.0/24',
                virtual_network_name=None, vnet_address_prefix='10.0.0.0/16',
                public_ip_address_type=None, subnet_type=None, validate=False,
                connection_draining_timeout=0, enable_http2=None, min_capacity=None, zones=None,
                custom_error_pages=None, firewall_policy=None, max_capacity=None,
                user_assigned_identity=None, enable_fips=None,
                enable_private_link=False,
                private_link_ip_address=None,
                private_link_subnet='PrivateLinkDefaultSubnet',
                private_link_subnet_prefix='10.0.1.0/24',
                private_link_primary=None,
                trusted_client_cert=None,
                ssl_profile=None,
                ssl_profile_id=None,
                ssl_cert_name=None):
        from azure.cli.core.util import random_string
        from azure.cli.core.commands.arm import ArmTemplateBuilder
        from azure.cli.command_modules.network._template_builder import (
            build_application_gateway_resource, build_public_ip_resource, build_vnet_resource)

        DeploymentProperties = cmd.get_models('DeploymentProperties', resource_type=ResourceType.MGMT_RESOURCE_RESOURCES)

        tags = tags or {}
        sku_tier = sku.split('_', 1)[0] if not _is_v2_sku(sku) else sku
        http_listener_protocol = 'https' if (cert_data or key_vault_secret_id) else 'http'
        private_ip_allocation = 'Static' if private_ip_address else 'Dynamic'
        virtual_network_name = virtual_network_name or '{}Vnet'.format(application_gateway_name)

        # Build up the ARM template
        master_template = ArmTemplateBuilder()
        ag_dependencies = []

        public_ip_id = public_ip_address if is_valid_resource_id(public_ip_address) else None
        subnet_id = subnet if is_valid_resource_id(subnet) else None

        network_id_template = resource_id(
            subscription=get_subscription_id(cmd.cli_ctx), resource_group=resource_group_name,
            namespace='Microsoft.Network')

        if subnet_type == 'new':
            ag_dependencies.append('Microsoft.Network/virtualNetworks/{}'.format(virtual_network_name))
            vnet = build_vnet_resource(
                cmd, virtual_network_name, location, tags, vnet_address_prefix, subnet,
                subnet_address_prefix,
                enable_private_link=enable_private_link,
                private_link_subnet=private_link_subnet,
                private_link_subnet_prefix=private_link_subnet_prefix)
            master_template.add_resource(vnet)
            subnet_id = '{}/virtualNetworks/{}/subnets/{}'.format(network_id_template,
                                                                virtual_network_name, subnet)

        if public_ip_address_type == 'new':
            ag_dependencies.append('Microsoft.Network/publicIpAddresses/{}'.format(public_ip_address))
            public_ip_sku = None
            if _is_v2_sku(sku):
                public_ip_sku = 'Standard'
                public_ip_address_allocation = 'Static'
            master_template.add_resource(build_public_ip_resource(cmd, public_ip_address, location,
                                                                tags,
                                                                public_ip_address_allocation,
                                                                None, public_ip_sku, None))
            public_ip_id = '{}/publicIPAddresses/{}'.format(network_id_template,
                                                            public_ip_address)

        private_link_subnet_id = None
        private_link_name = 'PrivateLinkDefaultConfiguration'
        private_link_ip_allocation_method = 'Dynamic'
        if enable_private_link:
            private_link_subnet_id = '{}/virtualNetworks/{}/subnets/{}'.format(network_id_template,
                                                                            virtual_network_name,
                                                                            private_link_subnet)
            private_link_ip_allocation_method = 'Static' if private_link_ip_address else 'Dynamic'

        app_gateway_resource = build_application_gateway_resource(
            cmd, application_gateway_name, location, tags, sku, sku_tier, capacity, servers, frontend_port,
            private_ip_address, private_ip_allocation, priority, cert_data, cert_password, key_vault_secret_id,
            http_settings_cookie_based_affinity, http_settings_protocol, http_settings_port,
            http_listener_protocol, routing_rule_type, public_ip_id, subnet_id,
            connection_draining_timeout, enable_http2, min_capacity, zones, custom_error_pages,
            firewall_policy, max_capacity, user_assigned_identity, enable_fips,
            enable_private_link, private_link_name,
            private_link_ip_address, private_link_ip_allocation_method, private_link_primary,
            private_link_subnet_id, trusted_client_cert, ssl_profile, ssl_profile_id, ssl_cert_name)

        app_gateway_resource['dependsOn'] = ag_dependencies
        master_template.add_variable(
            'appGwID',
            "[resourceId('Microsoft.Network/applicationGateways', '{}')]".format(
                application_gateway_name))
        master_template.add_resource(app_gateway_resource)
        master_template.add_output('applicationGateway', application_gateway_name, output_type='object')
        if cert_password:
            master_template.add_secure_parameter('certPassword', cert_password)

        template = master_template.build()
        parameters = master_template.build_parameters()

        # deploy ARM template
        deployment_name = 'ag_deploy_' + random_string(32)
        client = get_mgmt_service_client(cmd.cli_ctx, ResourceType.MGMT_RESOURCE_RESOURCES).deployments
        properties = DeploymentProperties(template=template, parameters=parameters, mode='incremental')
        Deployment = cmd.get_models('Deployment', resource_type=ResourceType.MGMT_RESOURCE_RESOURCES)
        deployment = Deployment(properties=properties)

        if validate:
            _log_pprint_template(template)
            if cmd.supported_api_version(min_api='2019-10-01', resource_type=ResourceType.MGMT_RESOURCE_RESOURCES):
                from azure.cli.core.commands import LongRunningOperation
                validation_poller = client.begin_validate(resource_group_name, deployment_name, deployment)
                return LongRunningOperation(cmd.cli_ctx)(validation_poller)

            return client.validate(resource_group_name, deployment_name, deployment)

        return sdk_no_wait(no_wait, client.begin_create_or_update, resource_group_name, deployment_name, deployment)
