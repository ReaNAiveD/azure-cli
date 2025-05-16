import timeit

from knack.log import get_logger

logger = get_logger(__name__)

class CommandIndex:
    from azure.cli.app.cli import AzCli

    _COMMAND_INDEX = 'commandIndex'
    _COMMAND_INDEX_VERSION = 'version'
    _COMMAND_INDEX_CLOUD_PROFILE = 'cloudProfile'

    def __init__(self, cli_ctx: AzCli | None = None, version=None):
        """Class to manage command index.

        :param cli_ctx: Only needed when `get` or `update` is called.
        """
        from azure.cli.core._session import INDEX
        self.INDEX = INDEX
        self.version = version
        if cli_ctx:
            self.cloud_profile = cli_ctx.cloud.profile
        self.cli_ctx = cli_ctx

    def get(self, args: list[str]):
        """Get the corresponding module and extension list of a command.

        :param args: command arguments, like ['network', 'vnet', 'create', '-h']
        :return: a tuple containing a list of modules and a list of extensions.
        """
        # If the command index version or cloud profile doesn't match those of the current command,
        # invalidate the command index.
        index_version = self.INDEX[self._COMMAND_INDEX_VERSION]
        cloud_profile = self.INDEX[self._COMMAND_INDEX_CLOUD_PROFILE]
        if not (index_version and index_version == self.version and
                cloud_profile and cloud_profile == self.cloud_profile):
            logger.debug("Command index version or cloud profile is invalid or doesn't match the current command.")
            self.invalidate()
            return None

        # Make sure the top-level command is provided, like `az version`.
        # Skip command index for `az` or `az --help`.
        if not args or args[0].startswith('-'):
            return None

        # Get the top-level command, like `network` in `network vnet create -h`
        top_command = args[0]
        index = self.INDEX[self._COMMAND_INDEX]
        # Check the command index for (command: [module]) mapping, like
        # "network": ["azure.cli.command_modules.natgateway", "azure.cli.command_modules.network", "azext_firewall"]
        index_modules_extensions = index.get(top_command)
        if not index_modules_extensions and self.cli_ctx.data['completer_active']:
            # If user type `az acco`, command begin with `acco` will be matched.
            logger.debug("In autocomplete mode, load commands starting with: '%s'", top_command)
            index_modules_extensions = []
            for command in index:
                if command.startswith(top_command):
                    index_modules_extensions += index[command]

        if index_modules_extensions:
            # This list contains both built-in modules and extensions
            index_builtin_modules = []
            index_extensions = []
            # Found modules from index
            logger.debug("Modules found from index for '%s': %s", top_command, index_modules_extensions)
            command_module_prefix = 'azure.cli.command_modules.'
            for m in index_modules_extensions:
                if m.startswith(command_module_prefix):
                    # The top-level command is from a command module
                    index_builtin_modules.append(m[len(command_module_prefix):])
                elif m.startswith('azext_'):
                    # The top-level command is from an extension
                    index_extensions.append(m)
                else:
                    logger.warning("Unrecognized module: %s", m)
            return index_builtin_modules, index_extensions

        return None

    def update(self, command_table):
        """Update the command index according to the given command table.

        :param command_table: The command table built by azure.cli.core.MainCommandsLoader.load_command_table
        """
        start_time = timeit.default_timer()
        self.INDEX[self._COMMAND_INDEX_VERSION] = self.version
        self.INDEX[self._COMMAND_INDEX_CLOUD_PROFILE] = self.cloud_profile
        from collections import defaultdict
        index = defaultdict(list)

        # self.cli_ctx.invocation.commands_loader.command_table doesn't exist in DummyCli due to the lack of invocation
        for command_name, command in command_table.items():
            # Get the top-level name: <vm> create
            top_command = command_name.split()[0]
            # Get module name, like azure.cli.command_modules.vm, azext_webapp
            module_name = command.loader.__module__
            if module_name not in index[top_command]:
                index[top_command].append(module_name)
        elapsed_time = timeit.default_timer() - start_time
        self.INDEX[self._COMMAND_INDEX] = index
        logger.debug("Updated command index in %.3f seconds.", elapsed_time)

    def invalidate(self):
        """Invalidate the command index.

        This function MUST be called when installing or updating extensions. Otherwise, when an extension
            1. overrides a built-in command, or
            2. extends an existing command group,
        the command or command group will only be loaded from the command modules as per the stale command index,
        making the newly installed extension be ignored.

        This function can be called when removing extensions.
        """
        self.INDEX[self._COMMAND_INDEX_VERSION] = ""
        self.INDEX[self._COMMAND_INDEX_CLOUD_PROFILE] = ""
        self.INDEX[self._COMMAND_INDEX] = {}
        logger.debug("Command index has been invalidated.")
