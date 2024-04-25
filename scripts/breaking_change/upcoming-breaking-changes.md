---
title: Upcoming Breaking Changes – Azure CLI | Microsoft Docs
description: Learn about breaking changes coming to Azure CLI in the next breaking change release
manager: jasongroce
author: dbradish-microsoft
ms.author: dbradish
ms.date: {{ date }}
ms.topic: article
ms.service: azure-cli
ms.tool: azure-cli
ms.custom: devx-track-azurecli, seo-azure-cli
keywords: azure cli updates, azure cli notes, azure cli versions, azure cli breaking changes
---

# Upcoming breaking changes in Azure CLI

{% for version, module_bc in breaking_changes | dictsort -%}
## Deprecated in {{ version }}

{% for module, command_bc in module_bc.items() -%}
### {{ module }}

{% for command, bcs in command_bc.items() -%}
#### `{{ command }}`

{% for bc in bcs -%}
- {{ bc }}
{% endfor %}

{% endfor -%}
{% endfor -%}
{% endfor -%}