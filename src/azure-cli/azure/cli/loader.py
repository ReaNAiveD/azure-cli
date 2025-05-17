# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
# pylint: disable=line-too-long

__version__ = "2.73.0"

from importlib import import_module
import pkgutil
import sys
import timeit
import traceback

from azure.cli.index import CommandIndex
from azure.cli.core import AzCommandsLoader, ModExtensionSuppress
from azure.cli.core.breaking_change import import_core_breaking_changes, import_extension_breaking_changes, import_module_breaking_changes
from azure.cli.core.commands import ExtensionCommandSource
from azure.cli.core.extension import Extension, get_extension_modname, get_extension_path, get_extensions
from knack.commands import CLICommandsLoader
from knack.log import get_logger
from knack.util import CLIError

logger = get_logger(__name__)

BLOCKED_MODS = ['context', 'shell', 'documentdb', 'component']
EVENT_FAILED_EXTENSION_LOAD = 'MainLoader.OnFailedExtensionLoad'

# [Reserved, in case of future usage]
# Modules that will always be loaded. They don't expose commands but hook into CLI core.
ALWAYS_LOADED_MODULES = []
# Extensions that will always be loaded if installed. They don't expose commands but hook into CLI core.
ALWAYS_LOADED_EXTENSIONS = ['azext_ai_examples', 'azext_next']


def _get_extension_suppressions(mod_loaders):
    res = []
    for m in mod_loaders:
        suppressions = getattr(m, 'suppress_extension', None)
        if suppressions:
            suppressions = suppressions if isinstance(suppressions, list) else [suppressions]
            for sup in suppressions:
                if isinstance(sup, ModExtensionSuppress):
                    res.append(sup)
    return res


class MainCommandsLoader(CLICommandsLoader):
    from azure.cli.core import AzCli

    # Format string for pretty-print the command module table
    header_mod = "%-20s %10s %9s %9s" % ("Name", "Load Time", "Groups", "Commands")
    item_format_string = "%-20s %10.3f %9d %9d"
    header_ext = header_mod + "  Directory"
    item_ext_format_string = item_format_string + "  %s"

    def __init__(self, cli_ctx: AzCli | None = None):
        super().__init__(cli_ctx)
        self.cmd_to_loader_map: dict[str, list[AzCommandsLoader]] = {}
        self.loaders: list[AzCommandsLoader] = []

    def _update_command_definitions(self):
        for cmd_name in self.command_table:
            loaders = self.cmd_to_loader_map[cmd_name]
            for loader in loaders:
                loader.command_table = self.command_table
                loader._update_command_definitions()  # pylint: disable=protected-access

    # pylint: disable=too-many-statements, too-many-locals
    def load_command_table(self, args):
        # Clear the tables to make this method idempotent
        self.command_group_table.clear()
        self.command_table.clear()

        # Import announced breaking changes in azure.cli.core._breaking_change.py
        import_core_breaking_changes()

        command_index = None
        # Set fallback=False to turn off command index in case of regression
        use_command_index = self.cli_ctx.config.getboolean('core', 'use_command_index', fallback=True)
        if use_command_index:
            command_index = CommandIndex(self.cli_ctx, self.cli_ctx.get_cli_version())
            index_result = command_index.get(args)
            if index_result:
                index_modules, index_extensions = index_result
                # Always load modules and extensions, because some of them (like those in
                # ALWAYS_LOADED_EXTENSIONS) don't expose a command, but hooks into handlers in CLI core
                self._update_command_table_from_modules(args, index_modules)
                # The index won't contain suppressed extensions
                self._update_command_table_from_extensions(args, [], index_extensions)

                logger.debug("Loaded %d groups, %d commands.", len(self.command_group_table), len(self.command_table))
                from azure.cli.core.util import roughly_parse_command
                # The index may be outdated. Make sure the command appears in the loaded command table
                raw_cmd = roughly_parse_command(args)
                for cmd in self.command_table:
                    if raw_cmd.startswith(cmd):
                        # For commands with positional arguments, the raw command won't match the one in the
                        # command table. For example, `az find vm create` won't exist in the command table, but the
                        # corresponding command should be `az find`.
                        # raw command  : az find vm create
                        # command table: az find
                        # remaining    :         vm create
                        logger.debug("Found a match in the command table.")
                        logger.debug("Raw command  : %s", raw_cmd)
                        logger.debug("Command table: %s", cmd)
                        remaining = raw_cmd[len(cmd) + 1:]
                        if remaining:
                            logger.debug("remaining    : %s %s", ' ' * len(cmd), remaining)
                        return self.command_table
                # For command group, it must be an exact match, as no positional argument is supported by
                # command group operations.
                if raw_cmd in self.command_group_table:
                    logger.debug("Found a match in the command group table for '%s'.", raw_cmd)
                    return self.command_table
                if self.cli_ctx.data['completer_active']:
                    # If the command is not complete in autocomplete mode, we should match shorter command.
                    # For example, `account sho` should match `account`.
                    logger.debug("Could not find a match in the command or command group table for '%s'", raw_cmd)
                    trimmed_raw_cmd = ' '.join(raw_cmd.split()[:-1])
                    logger.debug("In autocomplete mode, try to match trimmed raw cmd: '%s'", trimmed_raw_cmd)
                    if not trimmed_raw_cmd:
                        # If full command is 'az acc', raw_cmd is 'acc', trimmed_raw_cmd is ''.
                        logger.debug("Trimmed raw cmd is empty, return command table.")
                        return self.command_table
                    if trimmed_raw_cmd in self.command_group_table:
                        logger.debug("Found a match in the command group table for trimmed raw cmd: '%s'.",
                                     trimmed_raw_cmd)
                        return self.command_table

                logger.debug("Could not find a match in the command or command group table for '%s'. "
                             "The index may be outdated.", raw_cmd)
            else:
                logger.debug("No module found from index for '%s'", args)

        # No module found from the index. Load all command modules and extensions
        logger.debug("Loading all modules and extensions")
        self._update_command_table_from_modules(args)

        ext_suppressions = _get_extension_suppressions(self.loaders)
        # We always load extensions even if the appropriate module has been loaded
        # as an extension could override the commands already loaded.
        self._update_command_table_from_extensions(args, ext_suppressions)
        logger.debug("Loaded %d groups, %d commands.", len(self.command_group_table), len(self.command_table))

        if use_command_index:
            command_index.update(self.command_table)

        return self.command_table

    @staticmethod
    def _sort_command_loaders(command_loaders):
        module_command_loaders = []
        extension_command_loaders = []

        # Separate module and extension command loaders
        for loader in command_loaders:
            if loader.__module__.startswith('azext'):
                extension_command_loaders.append(loader)
            else:
                module_command_loaders.append(loader)

        # Sort name in each command loader list
        module_command_loaders.sort(key=lambda loader: loader.__class__.__name__)
        extension_command_loaders.sort(key=lambda loader: loader.__class__.__name__)

        # Module first, then extension
        sorted_command_loaders = module_command_loaders + extension_command_loaders
        return sorted_command_loaders

    def load_arguments(self, command=None):
        from azure.cli.core.commands.parameters import (
            resource_group_name_type, get_location_type, deployment_name_type, vnet_name_type, subnet_name_type)
        from knack.arguments import ignore_type

        # omit specific command to load everything
        if command is None:
            command_loaders = set()
            for loaders in self.cmd_to_loader_map.values():
                command_loaders = command_loaders.union(set(loaders))
            # sort command loaders for consistent order when loading all commands for docs generation to avoid random diff
            command_loaders = self._sort_command_loaders(command_loaders)
            logger.info('Applying %s command loaders...', len(command_loaders))
        else:
            command_loaders = self.cmd_to_loader_map.get(command, None)

        if command_loaders:
            for loader in command_loaders:

                # register global args
                with loader.argument_context('') as c:
                    c.argument('resource_group_name', resource_group_name_type)
                    c.argument('location', get_location_type(self.cli_ctx))
                    c.argument('vnet_name', vnet_name_type)
                    c.argument('subnet', subnet_name_type)
                    c.argument('deployment_name', deployment_name_type)
                    c.argument('cmd', ignore_type)

                if command is None:
                    # load all arguments via reflection
                    for cmd in loader.command_table.values():
                        cmd.load_arguments()  # this loads the arguments via reflection
                    loader.skip_applicability = True
                    loader.load_arguments('')  # this adds entries to the argument registries
                else:
                    loader.command_name = command
                    self.command_table[command].load_arguments()  # this loads the arguments via reflection
                    loader.load_arguments(command)  # this adds entries to the argument registries
                self.argument_registry.arguments.update(loader.argument_registry.arguments)
                self.extra_argument_registry.update(loader.extra_argument_registry)
                loader._update_command_definitions()  # pylint: disable=protected-access

    def _load_extension_command_loader(self, args, ext):
        return self._load_command_loader(args, ext, '')

    def _load_module_command_loader(self, args, mod):
        return self._load_command_loader(args, mod, 'azure.cli.command_modules.')

    def _init_command_loader(self, args, name, prefix) -> AzCommandsLoader | None:
        module = import_module(prefix + name)
        loader_cls = getattr(module, 'COMMAND_LOADER_CLS', None)
        if not loader_cls:
            try:
                get_command_loader = getattr(module, 'get_command_loader', None)
                loader_cls = get_command_loader(self.cli_ctx)
            except (ImportError, AttributeError, TypeError):
                logger.debug("Module '%s' is missing `get_command_loader` entry.", name)

        if loader_cls:
            return loader_cls(cli_ctx=self.cli_ctx)
        logger.debug("Module '%s' is missing `COMMAND_LOADER_CLS` entry.", name)
        return None

    def _load_command_loader(self, args, name, prefix):
        command_loader = self._init_command_loader(args, name, prefix)
        if command_loader:
            self.loaders.append(command_loader)  # This will be used by interactive
            if command_loader.supported_resource_type():
                command_table = command_loader.load_command_table(args)
                if command_table:
                    for cmd in list(command_table.keys()):
                        # TODO: If desired to for extension to patch module, this can be uncommented
                        # if self.cmd_to_loader_map.get(cmd):
                        #    self.cmd_to_loader_map[cmd].append(command_loader)
                        # else:
                        self.cmd_to_loader_map[cmd] = [command_loader]
        return command_loader

    def _update_command_table_from_modules(self, args: list[str], command_modules: list[str] | None = None):
        """Loads command tables from modules and merge into the main command table.

        :param args: Arguments of the command.
        :param list command_modules: Command modules to load, in the format like ['resource', 'profile'].
            If None, will do module discovery and load all modules.
            If [], only ALWAYS_LOADED_MODULES will be loaded.
            Otherwise, the list will be extended using ALWAYS_LOADED_MODULES.
        """

        # As command modules are built-in, the existence of modules in ALWAYS_LOADED_MODULES is NOT checked
        if command_modules is not None:
            command_modules.extend(ALWAYS_LOADED_MODULES)
        else:
            # Perform module discovery
            command_modules = []
            try:
                mods_ns_pkg = import_module('azure.cli.command_modules')
                command_modules = [modname for _, modname, _ in
                                    pkgutil.iter_modules(mods_ns_pkg.__path__)]
                logger.debug('Discovered command modules: %s', command_modules)
            except ImportError as e:
                logger.warning(e)

        count = 0
        cumulative_elapsed_time = 0
        cumulative_group_count = 0
        cumulative_command_count = 0
        logger.debug("Loading command modules:")
        logger.debug(self.header_mod)

        for mod in [m for m in command_modules if m not in BLOCKED_MODS]:
            try:
                start_time = timeit.default_timer()
                command_loader = self._load_module_command_loader(args, mod)
                import_module_breaking_changes(mod)
                module_command_table = command_loader.command_table
                module_group_table = command_loader.command_group_table
                for cmd in module_command_table.values():
                    cmd.command_source = mod
                self.command_table.update(module_command_table)
                self.command_group_table.update(module_group_table)

                elapsed_time = timeit.default_timer() - start_time
                logger.debug(self.item_format_string, mod, elapsed_time,
                                len(module_group_table), len(module_command_table))
                count += 1
                cumulative_elapsed_time += elapsed_time
                cumulative_group_count += len(module_group_table)
                cumulative_command_count += len(module_command_table)
            except Exception as ex:  # pylint: disable=broad-except
                # Changing this error message requires updating CI script that checks for failed
                # module loading.
                from azure.cli.core import telemetry
                logger.error("Error loading command module '%s': %s", mod, ex)
                telemetry.set_exception(exception=ex, fault_type='module-load-error-' + mod,
                                        summary='Error loading module: {}'.format(mod))
                logger.debug(traceback.format_exc())
        # Summary line
        logger.debug(self.item_format_string,
                        "Total ({})".format(count), cumulative_elapsed_time,
                        cumulative_group_count, cumulative_command_count)

    def _update_command_table_from_extensions(self, args: list[str], ext_suppressions: list[ModExtensionSuppress], extension_modname: list[str] | None = None):
        """Loads command tables from extensions and merge into the main command table.

        :param ext_suppressions: Extension suppression information.
        :param extension_modname: Command modules to load, in the format like ['azext_timeseriesinsights'].
            If None, will do extension discovery and load all extensions.
            If [], only ALWAYS_LOADED_EXTENSIONS will be loaded.
            Otherwise, the list will be extended using ALWAYS_LOADED_EXTENSIONS.
            If the extensions in the list are not installed, it will be skipped.
        """
        def _handle_extension_suppressions(extensions: list[Extension]) -> list[Extension]:
            filtered_extensions = []
            for ext in extensions:
                should_include = True
                for suppression in ext_suppressions:
                    if should_include and suppression.handle_suppress(ext):
                        should_include = False
                if should_include:
                    filtered_extensions.append(ext)
            return filtered_extensions

        def _filter_modname(extensions: list[Extension], extension_modname: list[str]) -> list[Extension]:
            # Extension's name may not be the same as its modname. eg. name: virtual-wan, modname: azext_vwan
            filtered_extensions: list[Extension] = []
            for ext in extensions:
                ext_mod = get_extension_modname(ext.name, ext.path)
                # Filter the extensions according to the index
                if ext_mod in extension_modname:
                    filtered_extensions.append(ext)
                    extension_modname.remove(ext_mod)
            if extension_modname:
                logger.debug("These extensions are not installed and will be skipped: %s", extension_modname)
            return filtered_extensions

        extensions = get_extensions()
        if extensions:
            if extension_modname is not None:
                extension_modname.extend(ALWAYS_LOADED_EXTENSIONS)
                extensions = _filter_modname(extensions, extension_modname)
            allowed_extensions = _handle_extension_suppressions(extensions)
            module_commands = set(self.command_table.keys())

            count = 0
            cumulative_elapsed_time = 0
            cumulative_group_count = 0
            cumulative_command_count = 0
            logger.debug("Loading extensions:")
            logger.debug(self.header_ext)

            for ext in allowed_extensions:
                try:
                    # Import in the `for` loop because `allowed_extensions` can be []. In such case we
                    # don't need to import `check_version_compatibility` at all.
                    from azure.cli.core.extension.operations import check_version_compatibility
                    check_version_compatibility(ext.get_metadata())
                except CLIError as ex:
                    # issue warning and skip loading extensions that aren't compatible with the CLI core
                    logger.warning(ex)
                    continue
                ext_name = ext.name
                ext_dir = ext.path or get_extension_path(ext_name)
                sys.path.append(ext_dir)
                try:
                    ext_mod = get_extension_modname(ext_name, ext_dir=ext_dir)
                    # Add to the map. This needs to happen before we load commands as registering a command
                    # from an extension requires this map to be up-to-date.
                    # self._mod_to_ext_map[ext_mod] = ext_name
                    start_time = timeit.default_timer()
                    extension_command_table, extension_group_table = \
                        self._load_extension_command_loader(args, ext_mod)
                    import_extension_breaking_changes(ext_mod)

                    for cmd_name, cmd in extension_command_table.items():
                        cmd.command_source = ExtensionCommandSource(
                            extension_name=ext_name,
                            overrides_command=cmd_name in module_commands,
                            preview=ext.preview,
                            experimental=ext.experimental)

                    self.command_table.update(extension_command_table)
                    self.command_group_table.update(extension_group_table)

                    elapsed_time = timeit.default_timer() - start_time
                    logger.debug(self.item_ext_format_string, ext_name, elapsed_time,
                                    len(extension_group_table), len(extension_command_table),
                                    ext_dir)
                    count += 1
                    cumulative_elapsed_time += elapsed_time
                    cumulative_group_count += len(extension_group_table)
                    cumulative_command_count += len(extension_command_table)
                except Exception as ex:  # pylint: disable=broad-except
                    self.cli_ctx.raise_event(EVENT_FAILED_EXTENSION_LOAD, extension_name=ext_name)
                    logger.warning("Unable to load extension '%s: %s'. Use --debug for more information.",
                                    ext_name, ex)
                    logger.debug(traceback.format_exc())
            # Summary line
            logger.debug(self.item_ext_format_string,
                            "Total ({})".format(count), cumulative_elapsed_time,
                            cumulative_group_count, cumulative_command_count, "")
