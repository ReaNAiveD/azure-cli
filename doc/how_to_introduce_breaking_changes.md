# How to introduce Breaking Changes in service command

## Breaking Changes in Azure CLI

A breaking change refers to a modification that disrupts backward compatibility with previous versions. When encountering such changes, user scripts might break.

To mitigate the impact of breaking changes, Azure CLI delays breaking changes and coordinates half-yearly **Breaking Change Releases** that bundle multiple breaking changes together. This approach helps users plan ahead and adapt to the modifications effectively.

### Breaking Change Window

The breaking change window *allows* for service command breaking changes. When a Pull Request is merged during this sprint, it will be included in the next Breaking Change Release.

The timing of the breaking change window in Azure CLI aligns with [Microsoft Build](https://build.microsoft.com/) and [Microsoft Ignite](https://ignite.microsoft.com/). You could find the next Breaking Change Release plan in our [milestones](https://github.com/Azure/azure-cli/milestones).

> If you would like to release ad-hoc breaking changes, reach out to the CLI team to provide an explanation for the necessity of these changes..

### Pre-announce Breaking Changes

All breaking changes **must** be pre-announced several sprints ahead Release. There are two approaches to inform both interactive users and automatic users about the breaking changes.

1. (**Mandatory**) Breaking Changes must be pre-announced through Warning Log while executing.
2. (*Automatic*) Breaking Changes would be collected automatically and listed in [Upcoming Breaking Change](https://learn.microsoft.com/en-us/cli/azure/upcoming-breaking-changes).

## Workflow

### Overview

* CLI Owned Module
  * Service Team should create an Issue that requests CLI Team to create the pre-announcement several sprints ahead Breaking Change Window.
    * Please ensure sufficient time for CLI Team to finish the feature.
  * The pre-announcement should be released ahead of Breaking Change Window.
* Service Owned Module
  * Service Team should create a Pull Request that create the pre-announcement several sprints ahead Breaking Change Window.
  * The pre-announcement should be released ahead of Breaking Change Window.
* After releasing the pre-announcement, a pipeline would be triggered and Upcoming Breaking Change Documentation would be updated.
* At the start of Breaking Change window, emails would be sent to notify Service Teams to adopt Breaking Changes.
* Breaking Changes should be adopted within Breaking Change Window.

### Pre-announce Breaking Changes

We recommend different approaches for different types of Breaking Changes.

#### Deprecation

If you would like to deprecate command groups, commands, arguments or options, please following the [deprecation guide](authoring_command_modules/authoring_commands.md#deprecating-commands-and-arguments) to add a pre-announcement.

A warning message would be produced when executing the deprecated command.

```This command has been deprecated and will be removed in version 2.1.0. Use `test show` instead.```

If you would like to break the deprecated usage automatically in a future version, set the `expiration` in deprecation information. The `expiration` should be the breaking change release version in our [milestones](https://github.com/Azure/azure-cli/milestones) if set.

#### Others

If you would like to do other custom breaking changes such as changing a normal argument to be required. Please add the warning in the following format.

```text
Upcoming Breaking Change: [Description] in [Target Version/Date/Event]. [More Description and Alternative]. To know more about [Short Summary], please visit [Doc Link].
```

Most of the field in message is optional. Please ensure the description.

The warnings with `Breaking Change` in `custom.py` would be collected and tracked automatically.

### Upcoming Breaking Change Documentation

The Upcoming Breaking Change Documentation is released every sprint. This document lists the expected breaking changes for the next Breaking Change Release. However, due to the implementation’s dependency on the Service Team, not all the listed Breaking Changes may be adopted.

The Upcoming Breaking Change Documentation includes:
* The deprecation targeted at the next Breaking Change Release;
* The commands warning 'Upcoming Breaking Change';
* Other manual items.
