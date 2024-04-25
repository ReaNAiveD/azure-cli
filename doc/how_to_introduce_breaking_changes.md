# How to introduce Breaking Changes in service command

Azure CLI has bi-annual breaking change releases coinciding with Microsoft **Build** and **Ignite**. Limiting breaking changes to twice a year provides a stable experience for customers while being able to keep up to date with the latest versions of Azure CLI and plan accordingly for announced breaking changes.

## Breaking Changes in Azure CLI

A breaking change refers to a modification that disrupts backward compatibility with previous versions. The breaking changes could cause a customer's script or automation written in a previous version to fail.

The common examples of breaking changes include:
* Modifying the names of parameters/commands.
* Modifying the input logic of parameters.
* Modifying the format or properties of result output.
* Modifying the current behavior model.
* Adding additional verification that changes CLI behavior.

To mitigate the impact of breaking changes, Azure CLI delays breaking changes and coordinates half-yearly **Breaking Change Releases** that bundle multiple breaking changes together. This approach helps users plan ahead and adapt to the modifications effectively.

### Breaking Change Window

The breaking change window *allows* for service command breaking changes. When a Pull Request is merged during this sprint, it will be included in the next Breaking Change Release.

The timing of the breaking change window in Azure CLI aligns with [Microsoft Build](https://build.microsoft.com/) and [Microsoft Ignite](https://ignite.microsoft.com/). You could find the next Breaking Change Release plan in our [milestones](https://github.com/Azure/azure-cli/milestones).

> If you would like to release ad-hoc breaking changes, reach out to the CLI team to provide an explanation for the necessity of these changes. The exceptions can be provide in the following cases:
> * The critical bugs need hotfix
> * The security patch
> * If server side has produced a breaking change which is inevitable for users, then CLI side has to adapt it
> 
> The above situation makes it necessary to introduce breaking change as soon as possible.

### Pre-announce Breaking Changes

All breaking changes **must** be pre-announced several sprints ahead Release. There are two approaches to inform both interactive users and automatic users about the breaking changes.

1. (**Mandatory**) Breaking Changes must be pre-announced through Warning Log while executing.
2. (*Automatic*) Breaking Changes would be collected automatically and listed in [Upcoming Breaking Change](https://learn.microsoft.com/en-us/cli/azure/upcoming-breaking-changes).

## Workflow

### Overview

* CLI Owned Module
  * Service Team should create an Issue that requests CLI Team to create the pre-announcement several sprints ahead Breaking Change Window. The CLI team will look at the issue and evaluate if it will be accepted in the next breaking change release.
    * Please ensure sufficient time for CLI Team to finish the pre-announcement.
  * The pre-announcement should be released ahead of Breaking Change Window.
* Service Owned Module
  * Service Team should create a Pull Request that create the pre-announcement several sprints ahead Breaking Change Window.
  * The pre-announcement should be released ahead of Breaking Change Window.
* After releasing the pre-announcement, a pipeline would be triggered, and the Upcoming Breaking Change Documentation would be updated.
* At the start of Breaking Change window, emails would be sent to notify Service Teams to adopt Breaking Changes.
* Breaking Changes should be adopted within Breaking Change Window.

### Pre-announce Breaking Changes

We recommend different approaches for different types of Breaking Changes.

#### Deprecation

If you would like to deprecate command groups, commands, arguments or options, please following the [deprecation guide](authoring_command_modules/authoring_commands.md#deprecating-commands-and-arguments) to add a pre-announcement.

```Python
from azure.cli.core.breaking_change import NEXT_BREAKING_CHANGE_RELEASE

with self.command_group('test', test_sdk) as g:
  g.command('show-parameters', 'get_params', deprecate_info=g.deprecate(redirect='test show', expiration=NEXT_BREAKING_CHANGE_RELEASE))
```

A warning message would be produced when executing the deprecated command.

```This command has been deprecated and will be removed in version 2.1.0. Use `test show` instead.```

If you would like to break the deprecated usage automatically in a future version, set the `expiration` in deprecation information. The `expiration` should be the breaking change release version in our [milestones](https://github.com/Azure/azure-cli/milestones) if set.

#### Others

If you would like to pre-announce other custom breaking changes such as a required argument change, please use BreakingChange.pre_announce() in src/azure-cli-core/azure/cli/core/breaking_change.py. This method generates a warning based on the constructed Breaking Change object.

```python
from knack.log import get_logger
logger = get_logger(__name__)


def create_foo(ctx, ):
    from azure.cli.core.breaking_change import BreakingChange, BreakingChangeType, NextBreakingChangeWindow
    
    # Pre-announce the requirement of the `--baz` parameter
    BreakingChange('az foo bar', 'The parameter `--baz` will be required', target_version=NextBreakingChangeWindow(), 
                   typ=BreakingChangeType.BeRequired, doc_link='http://foo.doc.link/bar').pre_announce(logger)

    # Handle the command logic
```

This would produce the following warning when calling the command:

```text
Upcoming Breaking Change: The parameter `--baz` will be required in next breaking change release(2.61.0). To know more about the Breaking Change, please visit http://foo.doc.link/bar.
```

> **Note**
> 
> Please use this exact method for pre-announcing Breaking Changes. 
> Please construct the BreakingChange object with literal strings and enum values only.
> 
> The Upcoming Breaking Change documentation depends on the static analysis of `BreakingChange.pre_announce()`.
> 
> Incorrect usage examples:
> ```python
> cmd = 'az foo bar'
> BreakingChange(cmd, 'The parameter `--baz` will be required').pre_announce(logger) # ❌
> BreakingChange('az foo bar', f'The parameter `{param}` will be required').pre_announce(logger) # ❌
> ```

## Upcoming Breaking Change Documentation

The Upcoming Breaking Change Documentation is released every sprint. This document lists the expected breaking changes for the next Breaking Change Release. However, due to the implementation’s dependency on the Service Team, not all the listed Breaking Changes may be adopted.

The Upcoming Breaking Change Documentation includes:
* The deprecation targeted at the next Breaking Change Release;
* The commands using `BreakingChange.pre_announce(logger)` to warn a breaking change;
* Other manual items.
