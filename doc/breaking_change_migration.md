# Breaking Change Migration Guidelines Design Document

## Motivation

Breaking changes in Azure CLI can significantly impact users who depend on specific behaviors or APIs in their workflows and automation scripts.

Currently, we lack a standardized approach to document and communicate these changes effectively. Users can only discover breaking changes through release notes, where critical migration information is often buried among other updates and may lack sufficient context or actionable guidance.

While we maintain an upcoming breaking changes document, it merely lists future breaking changes scheduled for the next major release. Users must still navigate through release notes to understand past breaking changes and their migration paths, creating a fragmented and user-unfriendly experience.

## Practice from Other Products

### Azure PowerShell

[Link to Azure PowerShell Breaking Change Migration Guide](https://learn.microsoft.com/en-us/powershell/azure/migrate-az-14.0.0?view=azps-14.3.0)

Azure PowerShell provides a dedicated documentation page for migration guidelines related to breaking changes. This page includes:
- Breaking change descriptions organized by each module.
- Migration guidelines which include a "Before" and "After" example for each breaking change.

Migration guide of Azure PowerShell is generated from the breaking change metadata of each command, which is also the source of the breaking change pre-announcement document.

### AWS CLI

[Link to AWS CLI Breaking Change Migration Guide](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html)

AWS CLI provides a dedicated documentation page for migration guidelines. This page includes:
- AWS CLI version 2 new features
- Breaking changes between AWS CLI version 1 and version 2

However, it includes breaking changes from version 1 to version 2 only, without consideration of breaking changes within version 2.

### Gradle

[Link to Gradle upgrading Guide](https://docs.gradle.org/current/userguide/upgrading_major_version_9.html)

Gradle provides a dedicated documentation page for upgrading guidelines. This page includes:
- Breaking change descriptions organized by different aspects of the tool.
- Each breaking change includes a description, an optional motivation and a migration guide with optional examples.

### dotNet

[Link to dotNet breaking changes](https://learn.microsoft.com/en-us/dotnet/core/compatibility/10.0)

DotNet core provides a dedicated set of documentation pages for breaking changes. Each page includes one single breaking change with:
- Description of the breaking change
- Previous behavior
- New behavior
- Version introduced
- Type of change
- Reason for change
- Recommended action
- Affected APIs

### Maven

[Link to Maven release notes](https://maven.apache.org/docs/3.9.11/release-notes.html)

Maven does not provide a dedicated migration guide for breaking changes. Instead, it includes potentially breaking core changes in its release notes.
Each item is a simple natural language description of the change, with a link to related JIRA issue for more details.

## Proposed Design

I provide two options for the design of the Breaking Change Migration Guidelines:
- Option 1: Add Breaking Change Migration Guidelines section in PR Template
- Option 2: Convert Upcoming Breaking Changes Announcement to Migration Guidelines

## Design Option 1: Breaking Change Migration Guidelines in PR Template

### Overview

This design option integrates breaking change migration guidelines directly into the pull request workflow by adding a dedicated section to the PR template. This approach captures migration guidance at the source - when breaking changes are implemented - and leverages existing automation pipelines to generate comprehensive documentation.

**Core Concept**: Service teams document migration guidelines within each PR that introduces breaking changes, and the release pipeline automatically collects these guidelines to generate a centralized migration documentation page.

### Solution Architecture

#### Data Collection
- Breaking change migration guidelines are documented within each PR description that introduces breaking changes
- Release pipeline aggregates all migration guidelines from merged PRs

#### Documentation Generation
- Automated pipeline step similar to current release notes generation
- Migration guidelines are compiled into a dedicated documentation page
- Content is organized by release version and affected services

### Implementation Details

#### PR Template Integration

The following section will be added to the PR template to capture migration guidelines:

````markdown
**Breaking Change Migration Guidelines**
<!--If your PR is a breaking change, please provide the migration guidelines for customers.-->

**Description:** Make sure that the description is clear and concise, explaining the purpose of the Breaking Change and how it affects users.
**Recommended Actions:** Provide clear instructions on how users can migrate to the new behavior or API.
**Previous Example:** If applicable, provide an example of the previous behavior or API that users were accustomed to.
```bash
// Example of the previous behavior
```
**New Example:** If applicable, provide an example of the new behavior or API that users should adopt.
```bash
// Example of the new behavior
```
**Links for more information:** If there are any relevant links, such as documentation or related issues, please include them here.


Only check the following items if breaking change is introduced.

- [ ] I have announced the breaking change at least 1 month in advance and deleted the announcement in this PR.
````

### Quality Assurance Process

We could ensure comprehensive migration guide coverage through a targeted review process for PRs most likely to introduce breaking changes:

- **Human Review**: All Pull Requests with "Breaking Change" in the title undergo mandatory human review to verify that appropriate migration guidelines are included
- **AI-Assisted Review**: GitHub Copilot integration helps identify missing migration content and suggests improvements to existing guidelines

### Roles and Responsibilities

#### Service Team Responsibilities

Service teams are responsible for creating comprehensive migration guidelines when introducing breaking changes. Their specific responsibilities include:

- **Clear Description**: Provide a concise explanation of what changed and why the change was necessary
- **Impact Assessment**: Clearly describe how the change affects existing users and workflows
- **Migration Steps**: Provide step-by-step instructions for adapting to the new behavior
- **Code Examples**: Include both "before" and "after" examples demonstrating the migration path

### Integration with Existing Processes

#### Upcoming Breaking Changes Announcement

The current process for announcing upcoming breaking changes will continue to be used for pre-announcements. Migration guidelines will be maintained separately, allowing for more detailed and flexible documentation of breaking changes.

#### Release Notes Coordination

**Open Discussion Point**: Integration approach with release notes generation.

*Recommendation*: Include breaking change migration guides in the same pull request as release notes but maintain them as separate files for better organization and specific use cases.

#### Breaking Change Detection Tool Integration

Enhance the breaking change detection tool with new notifications to remind service teams to provide migration guidelines when they introduce breaking changes.

### Special Considerations

#### Out-of-Window Breaking Changes

For breaking changes introduced outside the regular major release cycle, service teams should still provide migration guidelines using the PR template.

**Open Discussion Point**: Since out-of-window breaking changes may not follow the same timeline as regular releases, manual creation of migration guides for these changes should be considered.

### Benefits and Advantages

- **Workflow Integration**: Seamlessly integrates with existing development workflows without requiring changes to Azure CLI source code
- **Developer-Friendly**: Provides clear guidance for service teams on when and how to create migration guidelines
- **Automated Processing**: Leverages existing pipeline infrastructure for documentation generation
- **Quality Assurance**: Built-in review processes ensure comprehensive coverage and quality
- **Low Implementation Overhead**: Easy to implement with minimal disruption to current processes

## Design Option 2: Convert Upcoming Breaking Changes Announcement to Migration Guidelines

### Overview

This option transforms the existing upcoming breaking changes announcement system into a comprehensive migration guidelines framework. Instead of simply removing breaking change announcements when they take effect, this approach converts them into persistent migration guides maintained in source code.

The core concept involves transforming upcoming breaking change items into migration guide format during the breaking change implementation PR, then maintaining these guides in source code for extended periods to enable advanced features and better user support.

### Implementation Sub-Options

#### Sub-Option 2A: Manual Conversion with PR Writer Responsibility

**Conversion Process:**
1. **PR Writer Responsibility**: When implementing a breaking change, the PR writer transforms the existing announcement into a comprehensive migration guide within the same PR.
2. **Enhanced Content Requirements**: The conversion must include mandatory fields such as recommended actions, before/after examples, and step-by-step migration instructions.
3. **Review Process**: Both human reviewers and AI assistance (like Copilot) work together to ensure migration guides meet comprehensive standards.

**Content Requirements:**
- **Recommended Actions** (Mandatory): Clear, actionable steps for users to migrate
- **Before/After Examples**: Concrete code examples demonstrating the change
- **Impact Assessment**: Description of affected workflows and use cases

#### Sub-Option 2B: Automated Conversion with Manual Review

**Conversion Process:**
1. **Automated Transformation**: Pipeline automatically converts announcement format to migration guide format when breaking changes are implemented.
2. **Manual Enhancement**: PR writers and reviewers enhance the auto-generated content to ensure completeness.

### Data Structure and Persistence

The migration guides would use a different structure than the original announcements, designed specifically for post-implementation guidance:

- **Persistent Storage**: Migration guides remain in source code for at least one year after implementation
- **Enhanced Metadata**: Include version introduced, affected commands, migration complexity level
- **Retention Policy**: Guidelines for when migration guides can be archived or removed (to be defined based on usage patterns and version lifecycle)

### Advanced Capabilities

Maintaining migration guides in source code enables potential advanced features:

- **Error Handling Integration**: When users encounter errors caused by breaking changes, the system could provide relevant migration guidance (requires additional dedicated logic beyond the migration guides themselves)
- **First-Run Notifications**: Display relevant breaking changes when users run CLI for the first time with a new version
- **Contextual Help**: Integrate migration suggestions into CLI help systems

*Note: These advanced features represent potential capabilities enabled by this approach but are not part of the initial implementation scope.*

### Technical Considerations

- **Content Quality Assurance**: Ensure migration guidelines are comprehensive and actionable compared to original announcements
- **Historical Data Management**: Determine approach for handling breaking changes from previous release cycles
- **Integration with Existing Systems**: Coordinate with current breaking change detection and announcement workflows

### Pros

- **Source Code Integration**: Maintains migration information close to the code, enabling advanced runtime features
- **Centralized Management**: Provides a single source of truth for all historical breaking changes
- **Extended Support**: Enables long-term user support through persistent migration guidance
- **Enhanced Automation**: Potential for intelligent error handling and contextual user assistance

### Cons

- **Implementation Complexity**: Requires significant changes to existing breaking change processes
- **Maintenance Overhead**: Ongoing responsibility to maintain migration guides in source code
- **Workflow Integration**: Need to bridge different workflows between announcements and migration guidelines
- **Tooling Requirements**: May require additional tooling for effective management and automation
