# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
# pylint: disable=line-too-long

import os
import sys
import timeit

from knack.cli import CLI
from knack.commands import CLICommandsLoader
from knack.completion import ARGCOMPLETE_ENV_NAME
from knack.introspection import extract_args_from_signature, extract_full_summary_from_signature
from knack.log import get_logger
from knack.preview import PreviewItem
from knack.experimental import ExperimentalItem
from knack.util import CLIError
from knack.arguments import ArgumentsContext, CaseInsensitiveList  # pylint: disable=unused-import
from .local_context import AzCLILocalContext, LocalContextAction

logger = get_logger(__name__)

EXCLUDED_PARAMS = ['self', 'raw', 'polling', 'custom_headers', 'operation_config',
                   'content_version', 'kwargs', 'client', 'no_wait']


def _configure_knack():
    """Override consts defined in knack to make them Azure CLI-specific."""

    # Customize status tag messages.
    from knack.util import status_tag_messages
    ref_message = "Reference and support levels: https://aka.ms/CLI_refstatus"
    # Override the preview message.
    status_tag_messages['preview'] = "{} is in preview and under development. " + ref_message
    # Override the experimental message.
    status_tag_messages['experimental'] = "{} is experimental and under development. " + ref_message

    # Allow logs from 'azure' logger to be displayed.
    from knack.log import cli_logger_names
    cli_logger_names.append('azure')


_configure_knack()


class AzCli(CLI):

    def __init__(self, version, **kwargs):
        super().__init__(**kwargs)

        from azure.cli.core.breaking_change import register_upcoming_breaking_change_info
        from azure.cli.core.commands import register_cache_arguments
        from azure.cli.core.commands.arm import (
            register_ids_argument, register_global_subscription_argument)
        from azure.cli.core.cloud import get_active_cloud
        from azure.cli.core.commands.transform import register_global_transforms
        from azure.cli.core._session import ACCOUNT, CONFIG, SESSION, INDEX, VERSIONS
        from azure.cli.core.util import handle_version_update

        from knack.util import ensure_dir

        self.version = version

        self.data['headers'] = {}
        self.data['command'] = 'unknown'
        self.data['command_extension_name'] = None
        self.data['completer_active'] = ARGCOMPLETE_ENV_NAME in os.environ
        self.data['query_active'] = False

        azure_folder = self.config.config_dir
        ensure_dir(azure_folder)
        ACCOUNT.load(os.path.join(azure_folder, 'azureProfile.json'))
        CONFIG.load(os.path.join(azure_folder, 'az.json'))
        SESSION.load(os.path.join(azure_folder, 'az.sess'), max_age=3600)
        INDEX.load(os.path.join(azure_folder, 'commandIndex.json'))
        VERSIONS.load(os.path.join(azure_folder, 'versionCheck.json'))
        handle_version_update()

        self.cloud = get_active_cloud(self)
        logger.debug('Current cloud config:\n%s', str(self.cloud.name))
        register_global_transforms(self)
        register_global_subscription_argument(self)
        register_ids_argument(self)  # global subscription must be registered first!
        register_cache_arguments(self)
        register_upcoming_breaking_change_info(self)

        self.progress_controller = None

        self._configure_style()

    def refresh_request_id(self):
        """Assign a new random GUID as x-ms-client-request-id

        The method must be invoked before each command execution in order to ensure
        unique client-side request ID is generated.
        """
        import uuid
        self.data['headers']['x-ms-client-request-id'] = str(uuid.uuid1())

    def get_progress_controller(self, det=False, spinner=None):
        from azure.cli.core.commands import progress
        if not self.progress_controller:
            self.progress_controller = progress.ProgressHook()

        self.progress_controller.init_progress(progress.get_progress_view(det, spinner=spinner))
        return self.progress_controller

    def get_cli_version(self):
        return self.version

    def show_version(self):
        from azure.cli.core.util import get_az_version_string, show_updates

        ver_string, updates_available_components = get_az_version_string()
        print(ver_string)
        show_updates(updates_available_components)

    def exception_handler(self, ex):  # pylint: disable=no-self-use
        from azure.cli.core.util import handle_exception
        return handle_exception(ex)

    def _configure_style(self):
        from azure.cli.core.util import in_cloud_console
        from azure.cli.core.style import format_styled_text, get_theme_dict, Style

        # Configure Style
        if self.enable_color:
            theme = self.config.get('core', 'theme',
                                    fallback="cloud-shell" if in_cloud_console() else "dark")

            theme_dict = get_theme_dict(theme)

            if theme_dict:
                # If theme is used, also apply it to knack's logger
                from knack.util import color_map
                color_map['error'] = theme_dict[Style.ERROR]
                color_map['warning'] = theme_dict[Style.WARNING]
        else:
            theme = 'none'
        format_styled_text.theme = theme


class ModExtensionSuppress:  # pylint: disable=too-few-public-methods

    def __init__(self, mod_name, suppress_extension_name, suppress_up_to_version, reason=None, recommend_remove=False,
                 recommend_update=False):
        self.mod_name = mod_name
        self.suppress_extension_name = suppress_extension_name
        self.suppress_up_to_version = suppress_up_to_version
        self.reason = reason
        self.recommend_remove = recommend_remove
        self.recommend_update = recommend_update

    def handle_suppress(self, ext):
        from packaging.version import parse
        should_suppress = ext.name == self.suppress_extension_name and ext.version and \
            parse(ext.version) <= parse(self.suppress_up_to_version)
        if should_suppress:
            reason = self.reason or "Use --debug for more information."
            logger.warning("Extension %s (%s) has been suppressed. %s",
                           ext.name, ext.version, reason)
            logger.debug("Extension %s (%s) suppressed from being loaded due "
                         "to %s", ext.name, ext.version, self.mod_name)
            if self.recommend_remove:
                logger.warning("Remove this extension with 'az extension remove --name %s'", ext.name)
            if self.recommend_update:
                logger.warning("Update this extension with 'az extension update --name %s'", ext.name)
        return should_suppress


class AzCommandsLoader(CLICommandsLoader):  # pylint: disable=too-many-instance-attributes

    def __init__(self, cli_ctx=None, command_group_cls=None, argument_context_cls=None,
                 suppress_extension=None, **kwargs):
        from azure.cli.core.commands import AzCliCommand, AzCommandGroup, AzArgumentContext

        super().__init__(cli_ctx=cli_ctx,
                         command_cls=AzCliCommand,
                         excluded_command_handler_args=EXCLUDED_PARAMS)
        self.suppress_extension = suppress_extension
        self.module_kwargs = kwargs
        self.command_name = None
        self.skip_applicability = False
        self._command_group_cls = command_group_cls or AzCommandGroup
        self._argument_context_cls = argument_context_cls or AzArgumentContext

    def _update_command_definitions(self):
        master_arg_registry = self.cli_ctx.invocation.commands_loader.argument_registry
        master_extra_arg_registry = self.cli_ctx.invocation.commands_loader.extra_argument_registry

        for command_name, command in self.command_table.items():
            # Add any arguments explicitly registered for this command
            for argument_name, argument_definition in master_extra_arg_registry[command_name].items():
                command.arguments[argument_name] = argument_definition

            for argument_name in command.arguments:
                overrides = master_arg_registry.get_cli_argument(command_name, argument_name)
                command.update_argument(argument_name, overrides)

    def _apply_doc_string(self, dest, command_kwargs):
        from azure.cli.core.profiles._shared import APIVersionException
        doc_string_source = command_kwargs.get('doc_string_source', None)
        if not doc_string_source:
            return
        if not isinstance(doc_string_source, str):
            raise CLIError("command authoring error: applying doc_string_source '{}' directly will cause slowdown. "
                           'Import by string name instead.'.format(doc_string_source.__name__))

        model = doc_string_source
        try:
            model = self.get_models(doc_string_source)
        except APIVersionException:
            model = None
        if not model:
            from importlib import import_module
            (path, model_name) = doc_string_source.split('#', 1)
            method_name = None
            if '.' in model_name:
                (model_name, method_name) = model_name.split('.', 1)
            module = import_module(path)
            model = getattr(module, model_name)
            if method_name:
                model = getattr(model, method_name, None)
        if not model:
            raise CLIError("command authoring error: source '{}' not found.".format(doc_string_source))
        dest.__doc__ = model.__doc__

    def _get_resource_type(self):
        resource_type = self.module_kwargs.get('resource_type', None)
        if not resource_type:
            command_type = self.module_kwargs.get('command_type', None)
            resource_type = command_type.settings.get('resource_type', None) if command_type else None
        return resource_type

    def get_api_version(self, resource_type=None, operation_group=None):
        from azure.cli.core.profiles import get_api_version
        resource_type = resource_type or self._get_resource_type()
        version = get_api_version(self.cli_ctx, resource_type)
        if isinstance(version, str):
            return version
        version = getattr(version, operation_group, None)
        if version:
            return version
        from azure.cli.core.profiles._shared import APIVersionException
        raise APIVersionException(operation_group, self.cli_ctx.cloud.profile)

    def supported_api_version(self, resource_type=None, min_api=None, max_api=None, operation_group=None):
        from azure.cli.core.profiles import supported_api_version
        if not min_api and not max_api:
            # optimistically assume that fully supported if no api restriction listed
            return True
        api_support = supported_api_version(
            cli_ctx=self.cli_ctx,
            resource_type=resource_type or self._get_resource_type(),
            min_api=min_api,
            max_api=max_api,
            operation_group=operation_group)
        if isinstance(api_support, bool):
            return api_support
        if operation_group:
            return getattr(api_support, operation_group)
        return api_support

    def supported_resource_type(self, resource_type=None):
        from azure.cli.core.profiles import supported_resource_type
        return supported_resource_type(
            cli_ctx=self.cli_ctx,
            resource_type=resource_type or self._get_resource_type())

    def get_sdk(self, *attr_args, **kwargs):
        from azure.cli.core.profiles import get_sdk
        return get_sdk(self.cli_ctx, kwargs.pop('resource_type', self._get_resource_type()),
                       *attr_args, **kwargs)

    def get_models(self, *attr_args, **kwargs):
        from azure.cli.core.profiles import get_sdk
        resource_type = kwargs.get('resource_type', self._get_resource_type())
        operation_group = kwargs.get('operation_group', self.module_kwargs.get('operation_group', None))
        return get_sdk(self.cli_ctx, resource_type, *attr_args, mod='models', operation_group=operation_group)

    def command_group(self, group_name, command_type=None, **kwargs):
        if command_type:
            kwargs['command_type'] = command_type
        if 'deprecate_info' in kwargs:
            kwargs['deprecate_info'].target = group_name
        if kwargs.get('is_preview', False):
            kwargs['preview_info'] = PreviewItem(
                cli_ctx=self.cli_ctx,
                target=group_name,
                object_type='command group'
            )
        if kwargs.get('is_experimental', False):
            kwargs['experimental_info'] = ExperimentalItem(
                cli_ctx=self.cli_ctx,
                target=group_name,
                object_type='command group'
            )
        return self._command_group_cls(self, group_name, **kwargs)

    def argument_context(self, scope, **kwargs):
        return self._argument_context_cls(self, scope, **kwargs)

    # Please use add_cli_command instead of _cli_command.
    # Currently "keyvault" and "batch" modules are still rely on this function, so it cannot be removed now.
    def _cli_command(self, name, operation=None, handler=None, argument_loader=None, description_loader=None, **kwargs):

        from knack.deprecation import Deprecated

        kwargs['deprecate_info'] = Deprecated.ensure_new_style_deprecation(self.cli_ctx, kwargs, 'command')

        if operation and not isinstance(operation, str):
            raise TypeError("Operation must be a string. Got '{}'".format(operation))
        if handler and not callable(handler):
            raise TypeError("Handler must be a callable. Got '{}'".format(operation))
        if bool(operation) == bool(handler):
            raise TypeError("Must specify exactly one of either 'operation' or 'handler'")

        name = ' '.join(name.split())

        client_factory = kwargs.get('client_factory', None)

        def default_command_handler(command_args):
            from azure.cli.core.util import get_arg_list, augment_no_wait_handler_args
            from azure.cli.core.commands.client_factory import resolve_client_arg_name

            op = handler or self.get_op_handler(operation, operation_group=kwargs.get('operation_group'))
            op_args = get_arg_list(op)
            cmd = command_args.get('cmd') if 'cmd' in op_args else command_args.pop('cmd')

            client = client_factory(cmd.cli_ctx, command_args) if client_factory else None
            supports_no_wait = kwargs.get('supports_no_wait', None)
            if supports_no_wait:
                no_wait_enabled = command_args.pop('no_wait', False)
                augment_no_wait_handler_args(no_wait_enabled, op, command_args)
            if client:
                client_arg_name = resolve_client_arg_name(operation, kwargs)
                if client_arg_name in op_args:
                    command_args[client_arg_name] = client
            return op(**command_args)

        def default_arguments_loader():
            op = handler or self.get_op_handler(operation, operation_group=kwargs.get('operation_group'))
            self._apply_doc_string(op, kwargs)
            cmd_args = list(extract_args_from_signature(op, excluded_params=self.excluded_command_handler_args))
            return cmd_args

        def default_description_loader():
            op = handler or self.get_op_handler(operation, operation_group=kwargs.get('operation_group'))
            self._apply_doc_string(op, kwargs)
            return extract_full_summary_from_signature(op)

        kwargs['arguments_loader'] = argument_loader or default_arguments_loader
        kwargs['description_loader'] = description_loader or default_description_loader

        if self.supported_api_version(resource_type=kwargs.get('resource_type'),
                                      min_api=kwargs.get('min_api'),
                                      max_api=kwargs.get('max_api'),
                                      operation_group=kwargs.get('operation_group')):
            self._populate_command_group_table_with_subgroups(' '.join(name.split()[:-1]))
            self.command_table[name] = self.command_cls(self, name,
                                                        handler or default_command_handler,
                                                        **kwargs)

    def add_cli_command(self, name, command_operation, **kwargs):
        """Register a command in command_table with command operation provided"""
        from knack.deprecation import Deprecated
        from .commands.command_operation import BaseCommandOperation
        if not issubclass(type(command_operation), BaseCommandOperation):
            raise TypeError("CommandOperation must be an instance of subclass of BaseCommandOperation."
                            " Got instance of '{}'".format(type(command_operation)))

        kwargs['deprecate_info'] = Deprecated.ensure_new_style_deprecation(self.cli_ctx, kwargs, 'command')

        name = ' '.join(name.split())

        if self.supported_api_version(resource_type=kwargs.get('resource_type'),
                                      min_api=kwargs.get('min_api'),
                                      max_api=kwargs.get('max_api'),
                                      operation_group=kwargs.get('operation_group')):
            self._populate_command_group_table_with_subgroups(' '.join(name.split()[:-1]))
            self.command_table[name] = self.command_cls(loader=self,
                                                        name=name,
                                                        handler=command_operation.handler,
                                                        arguments_loader=command_operation.arguments_loader,
                                                        description_loader=command_operation.description_loader,
                                                        command_operation=command_operation,
                                                        **kwargs)

    def get_op_handler(self, operation, operation_group=None):
        """ Import and load the operation handler """
        # Patch the unversioned sdk path to include the appropriate API version for the
        # resource type in question.
        from importlib import import_module
        import types

        from azure.cli.core.profiles import AZURE_API_PROFILES
        from azure.cli.core.profiles._shared import get_versioned_sdk_path

        for rt in AZURE_API_PROFILES[self.cli_ctx.cloud.profile]:
            if operation.startswith(rt.import_prefix + '.'):
                operation = operation.replace(rt.import_prefix,
                                              get_versioned_sdk_path(self.cli_ctx.cloud.profile, rt,
                                                                     operation_group=operation_group))
                break

        try:
            mod_to_import, attr_path = operation.split('#')
            op = import_module(mod_to_import)
            for part in attr_path.split('.'):
                op = getattr(op, part)
            if isinstance(op, types.FunctionType):
                return op
            return op.__func__
        except (ValueError, AttributeError):
            raise ValueError("The operation '{}' is invalid.".format(operation))


def get_default_cli(
        cli_name: str,
        version: str,
        commands_loader_cls: type[CLICommandsLoader],
        *,
        config_dir: str | None = None,
        config_env_var_prefix: str | None = None,
        invocation_cls=None,
        parser_cls=None,
        logging_cls=None,
        output_cls=None,
        help_cls=None,
    ) -> AzCli:
    from azure.cli.core.azlogging import AzCliLogging
    from azure.cli.core.commands import AzCliCommandInvoker
    from azure.cli.core.parser import AzCliCommandParser
    from azure.cli.core._config import GLOBAL_CONFIG_DIR, ENV_VAR_PREFIX
    from azure.cli.core._help import AzCliHelp
    from azure.cli.core._output import AzOutputProducer

    return AzCli(
        version=version,
        cli_name=cli_name,
        config_dir=config_dir or GLOBAL_CONFIG_DIR,
        config_env_var_prefix=config_env_var_prefix or ENV_VAR_PREFIX,
        commands_loader_cls=commands_loader_cls,
        invocation_cls=invocation_cls or AzCliCommandInvoker,
        parser_cls=parser_cls or AzCliCommandParser,
        logging_cls=logging_cls or AzCliLogging,
        output_cls=output_cls or AzOutputProducer,
        help_cls=help_cls or AzCliHelp)
