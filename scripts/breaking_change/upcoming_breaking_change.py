import ast
import datetime
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

import requests


NextBreakingChangeWindow = 'NextBreakingChangeWindow'

ExtMetadataUrl = 'https://azcmdchangemgmt.blob.core.windows.net/cmd-metadata-per-version/azure-cli-extensions'

logger = logging.getLogger(__name__)


from jinja2 import Template

SCRIPTS_LOCATION = os.path.abspath(os.path.join('', 'scripts'))

TEMPLATE_FILE = os.path.join(SCRIPTS_LOCATION, "breaking_change", "upcoming-breaking-changes.md")


def next_breaking_change_version(core_repo_path):
    definition_file = os.path.join(core_repo_path, 'src', 'azure-cli-core', 'azure', 'cli', 'core', 'breaking_change.py')
    with open(definition_file, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    match = re.search(r'NEXT_BREAKING_CHANGE_RELEASE *= *\'(?P<version>[\d.]+)\'', content)
    version = match.group('version')
    return version


class BreakingChange:
    def __init__(self, module, command, detail, target_version):
        self.module = module
        self.command = command
        self.detail = detail
        self.target_version = target_version

    @classmethod
    def from_deprecate_info(cls, deprecate_info, options, module, command, typ):
        if typ in ['parameter', 'option']:
            if options:
                typ = f'{typ} `{"/".join(options)}`'
            elif 'target' in deprecate_info:
                typ = f'{typ} `{deprecate_info["target"]}`'
            elif 'name' in deprecate_info:
                typ = f'{typ} `{deprecate_info["name"]}`'
        replace = f' and replaced by `{deprecate_info["redirect"]}`' if 'redirect' in deprecate_info else ''
        detail = f'This {typ} is deprecated{replace}.'
        return cls(module, command, detail, deprecate_info.get('expiration'))


# region PreAnnouncement
def __func_name__(call):
    return __attr_of__(call.func, 'id') or __attr_of__(call.func, 'attr')


def __attr_of__(target, name):
    try:
        return target.__getattribute__(name)
    except AttributeError:
        return None


def __param_value__(call, pos, name):
    try:
        return call.args[pos]
    except IndexError:
        for keyword in call.keywords:
            if keyword.arg == name:
                return keyword.value
    return None


class UpcomingBreakingChangeScanner(ast.NodeVisitor):
    def __init__(self):
        self.changes = []
        self.cur_module = None

    def _scan(self, file_path):
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            parsed_code = ast.parse(f.read(), file_path)
        self.visit(parsed_code)

    def visit_Call(self, node):
        func_name = __func_name__(node)
        if func_name == 'BreakingChange':
            change = self.handle_breaking_change(node)
            if change:
                self.changes.append(change)
        else:
            return self.generic_visit(node)

    def handle_breaking_change(self, call):
        target = __param_value__(call, 0, 'command')
        desc = __param_value__(call, 1, 'desc')
        target_version = __param_value__(call, 2, 'target_version')
        typ = __param_value__(call, 3, 'typ')
        alter = __param_value__(call, 4, 'alter')
        doc_link = __param_value__(call, 5, 'doc_link')
        command = target.value.split(' -')[0]
        command = re.sub('^az +', '', command)
        target_version = self.handle_target_version(target_version)

        alter = f' Please use {alter.value} instead.' if alter else ''
        link = f' To know more about the Breaking Change, please visit {doc_link.value}.' if doc_link else ''
        detail = f'{desc.value}.{alter}{link}'
        return BreakingChange(self.cur_module, command, detail, target_version)

    @staticmethod
    def handle_target_version(node):
        if node is None:
            return NextBreakingChangeWindow
        if isinstance(node, str):
            return node
        func_name = __func_name__(node)
        if func_name == 'NextBreakingChangeWindow':
            return NextBreakingChangeWindow
        elif func_name == 'ExactVersion':
            version = __param_value__(node, 0, 'version')
            return version.value if version else None
        return None

    def scan_module(self, module_path, module_name):
        self.cur_module = module_name
        for (dirpath, _, filenames) in os.walk(module_path):
            for file in filenames:
                if not file.endswith('.py') or file.startswith('test_') or 'vendored_sdks' in dirpath:
                    continue
                file_path = os.path.join(dirpath, file)
                self._scan(file_path)
        self.cur_module = None

    def scan_core_repo(self, core_repo):
        modules_path = os.path.join(core_repo, 'src', 'azure-cli', 'azure', 'cli', 'command_modules')
        for module in os.listdir(modules_path):
            module_path = os.path.join(modules_path, module)
            self.scan_module(module_path, module)

    def scan_extension(self, extension):
        ext_src_path = os.path.join(extension, 'src')
        for ext in os.listdir(ext_src_path):
            ext_path = os.path.join(ext_src_path, ext)
            self.scan_module(ext_path, ext)


def collect_from_pre_announce(core_repo_path, extension_path):
    scanner = UpcomingBreakingChangeScanner()
    if core_repo_path:
        scanner.scan_core_repo(core_repo_path)
    if extension_path:
        scanner.scan_extension(extension_path)
    return scanner.changes
# endregion


# region DeprecateInfo
def handle_meta_dir(meta_dir):
    if not os.path.exists(meta_dir):
        raise RuntimeError(f"Azure CLI Metadata Directory ({meta_dir}) not Exists")
    for file in os.listdir(meta_dir):
        path = os.path.join(meta_dir, file)
        yield from handle_meta_file(path)


def handle_meta_file(file_path):
    if not os.path.exists(file_path):
        raise RuntimeError(f"Meta File ({file_path}) not Found.")
    with open(file_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
        yield from handle_module(meta)


def handle_module(module_meta):
    yield from handle_group(module_meta, module_meta['module_name'])


def handle_group(group_meta, module_name):
    if 'deprecate_info' in group_meta:
        yield BreakingChange.from_deprecate_info(group_meta['deprecate_info'], None, module_name,
                                                 group_meta['name'], 'command group')
    for cmd, cmd_meta in group_meta['commands'].items():
        yield from handle_command(cmd_meta, module_name)
    for sub_group_meta in group_meta['sub_groups'].values():
        yield from handle_group(sub_group_meta, module_name)


def handle_command(cmd_meta, module_name):
    if 'deprecate_info' in cmd_meta:
        yield BreakingChange.from_deprecate_info(cmd_meta['deprecate_info'], None, module_name,
                                                 cmd_meta['name'], 'command')
    for param in cmd_meta['parameters']:
        if param.get('name') == 'resource_group_name':
            continue
        if 'deprecate_info' in param:
            yield BreakingChange.from_deprecate_info(param['deprecate_info'], param['options'], module_name,
                                                     cmd_meta['name'], 'parameter')
        if 'options_deprecate_info' in param:
            for item in handle_options_deprecate_info(param['options_deprecate_info']):
                yield BreakingChange.from_deprecate_info(item, None, module_name, cmd_meta['name'], 'option')


def handle_options_deprecate_info(info_list):
    def get_redirect(item):
        return {k: item[k] for k in item if k != 'target'}

    kv = defaultdict(lambda: [])
    for info in info_list:
        rd = get_redirect(info)
        kv[json.dumps(rd)].append(info['target'])
    for key, targets in kv.items():
        yield {'target': '/'.join(targets), **json.loads(key)}


def collect_from_metadata(metadata_path):
    return list(handle_meta_dir(metadata_path))
# endregion


def _requests_get(url, retry=3, param=None, **kwargs):
    while retry > 0:
        try:
            resp = requests.get(url, param, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if retry > 0:
                logger.warning(f'Request Failed: {e}. Retrying...')
                retry -= 1
    return None


def iter_ext_meta_url():
    ext_list_url = f'{ExtMetadataUrl}/module_list.txt'
    resp = _requests_get(ext_list_url)
    if not resp:
        return
    for ext in resp.text.splitlines():
        version_list_url = f'{ExtMetadataUrl}/{ext}/version_list.txt'
        resp = _requests_get(version_list_url)
        if not resp:
            continue
        versions = resp.text.strip(' \n\r').splitlines()
        if not versions:
            continue
        latest_version = versions[-1]
        yield f'{ExtMetadataUrl}/{ext}/{latest_version}'


def handle_ext_meta_url(meta_url):
    resp = _requests_get(meta_url)
    metadata = resp.json()
    return list(handle_module(metadata))


def yield_from_ext_metadata():
    pool = ThreadPoolExecutor()
    fs = []
    for meta_url in iter_ext_meta_url():
        fs.append(pool.submit(handle_ext_meta_url, meta_url))
    for bks in as_completed(fs):
        for bk in bks.result():
            yield bk


def collect_from_ext_metadata():
    return list(yield_from_ext_metadata())


def collect_breaking_changes(core_repo, core_repo_metadata_dir, need_ext=False, ext_repo=None):
    breaking_changes = []
    breaking_changes.extend(collect_from_pre_announce(core_repo, ext_repo if need_ext else None))
    breaking_changes.extend(collect_from_metadata(core_repo_metadata_dir))
    if need_ext:
        breaking_changes.extend(collect_from_ext_metadata())
    return breaking_changes


def aggregate_breaking_changes(breaking_changes, next_bc_version):
    command_bc = lambda: defaultdict(lambda: [])
    module_bc = lambda: defaultdict(command_bc)
    version_bc = defaultdict(module_bc)
    for bc in breaking_changes:
        target_version = bc.target_version
        if target_version == NextBreakingChangeWindow:
            target_version = next_bc_version
        if target_version is None:
            target_version = 'Unspecific'
        if bc.detail not in version_bc[target_version][bc.module][bc.command]:
            version_bc[target_version][bc.module][bc.command].append(bc.detail)
    return version_bc


def generate_doc(breaking_changes):
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as doc_template:
        template = Template(doc_template.read(), trim_blocks=True)
    if template is None:
        raise RuntimeError("Failed to read template file {}".format(TEMPLATE_FILE))
    return template.render(
            breaking_changes=breaking_changes,
            date=datetime.date.today().strftime("%m/%d/%Y"))


def upcoming_breaking_change(core_repo, core_repo_metadata_dir, need_ext=False, ext_repo=None):
    bc = collect_breaking_changes(core_repo, core_repo_metadata_dir, need_ext, ext_repo)
    bc = aggregate_breaking_changes(bc, core_repo)
    doc_content = generate_doc(bc)
    print(doc_content)


if __name__ == '__main__':
    upcoming_breaking_change('.', '../azure-cli-dev-tools/CLI_META', True, '../azure-cli-extensions')
