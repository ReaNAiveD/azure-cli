# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import sys
from azure.cli.core import get_default_cli
from azure.cli.command_modules.monitor import MonitorCommandsLoader


try:
    from importlib.metadata import version

    cli = get_default_cli(
        cli_name='az-monitor',
        version=version('azure-cli-monitor'),
        commands_loader_cls=MonitorCommandsLoader,
    )

    exit_code = cli.invoke(sys.argv[1:])

    sys.exit(exit_code)

except KeyboardInterrupt:
    sys.exit(1)
except SystemExit as ex:  # some code directly call sys.exit, this is to make sure command metadata is logged
    exit_code = ex.code if ex.code is not None else 1
    raise ex
