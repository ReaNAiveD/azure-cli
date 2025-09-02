**Related command**
<!--- Please provide the related command with az {command} if you can, so that we can quickly route to the related person to review. --->

**Description**<!--Mandatory-->
<!--Why this PR? What is changed? What is the effect? etc. A high-quality description can accelerate the review process.-->

**Testing Guide**
<!--Example commands with explanations.-->

**History Notes**
<!--If your PR is not customer-facing, use {Component Name} in the PR title. Otherwise, use [Component Name] to allow our pipeline to add the title as a history note. If you need multiple history notes or would like to overwrite the note from the PR title, please fill in the following templates.-->

[Component Name 1] BREAKING CHANGE: `az command a`: Make some customer-facing breaking change
[Component Name 2] `az command b`: Add some customer-facing feature

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

---

This checklist is used to make sure that common guidelines for a pull request are followed.

- [ ] The PR title and description has followed the guideline in [Submitting Pull Requests](https://github.com/Azure/azure-cli/tree/dev/doc/authoring_command_modules#submitting-pull-requests).

- [ ] I adhere to the [Command Guidelines](https://github.com/Azure/azure-cli/blob/dev/doc/command_guidelines.md).

- [ ] I adhere to the [Error Handling Guidelines](https://github.com/Azure/azure-cli/blob/dev/doc/error_handling_guidelines.md).

Only check the following items if breaking change is introduced.

- [ ] I have announced the breaking change at least 1 month in advance and deleted the announcement in this PR.
