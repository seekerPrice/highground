# Issue tracker: GitHub

Specs and implementation tickets live in GitHub Issues for seekerPrice/highground. Use the authenticated gh CLI; verify the remote before mutation. Do not create GitHub automation.

Create one parent specification issue and one issue per approved Section 12 task, preserving Task 1–22 numbering and titles. Record the task number independently of GitHub's issue number. Link each task to the spec and its preceding execution gate; use native blocking dependencies when available, otherwise explicit Blocked by references. Shoulds depend on deployed acceptance of Tasks 1–17 and explicit task authorization; calendar allocations never delay earlier completion.

Read full issue bodies, labels and comments before work. For multiline issue bodies and comments, use a temporary text file with --body-file. Apply ready-for-agent only when scope is resolved; it never overrides the user's Task N authorization gate. Use needs-info for unresolved decisions. Do not close the parent spec just because individual tickets are created.

PRs as a request surface: no.

The user authorized GitHub setup and the original Section 12 task breakdown. Publish that scope as one parent spec and 22 task issues. Clearly mark proposed spec amendments and unresolved decisions; publication never makes those proposals approved or authorizes implementation. Reconfirm only changed scope or genuinely unresolved decisions. Completion comments include acceptance evidence and known limitations. No external messaging beyond the authorized project issue work.
