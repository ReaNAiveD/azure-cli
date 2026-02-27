from azure.cli.core.util import sdk_no_wait
from azure.cli.core.aaz import register_command
from azure.cli.core.commands import CLICommandArgument, DeploymentOutputLongRunningOperation, OperationCommand
from azure.cli.core.commands.arm import (
    ResourceType, deployment_validate_table_format, handle_template_based_exception)
from azure.cli.core.commands.client_factory import get_subscription_id, get_mgmt_service_client
from azure.cli.command_modules.network._validators import process_ag_create_namespace
from azure.mgmt.core.tools import parse_resource_id, is_valid_resource_id, resource_id
from knack.introspection import extract_args_from_signature
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
    AZ_NAME = None
    AZ_CONFIRMATION = False

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
