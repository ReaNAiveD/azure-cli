# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
# pylint: disable=line-too-long

import os

from knack.cli import CLI
from knack.completion import ARGCOMPLETE_ENV_NAME
from knack.log import get_logger

logger = get_logger(__name__)


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

    def __init__(self, **kwargs):
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
        from importlib.metadata import version
        return version('azure-cli')

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
