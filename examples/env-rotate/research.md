# Research: "Leaked your .env? Rotate the key first" (duo sketch, 2026-10-26)

Checked on 2026-10-26.

| Claim (screen / voice / caption / guide) | Source | Checked |
|---|---|---|
| "Rotate the key" is the first step after a secret is pushed (docs: "as a first step you need to revoke and/or rotate that secret") | https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository | 2026-10-26 |
| "Old key, dead key. It opens nothing now." (docs: a revoked secret "can no longer be used for access") | same page | 2026-10-26 |
| "It's not your fork" / "Forks keep everything" / "forks and clones keep a copy" (docs: "If the commit that introduced the sensitive data exists in any forks, it will continue to be accessible there."; "You cannot remove sensitive data from other users' clones of your repository.") | same page | 2026-10-26 |
| Deleting / force-pushing the commit isn't enough (docs: after rewriting and force-pushing, "the commits with sensitive data may still be accessible elsewhere") | same page | 2026-10-26 |
| "Clean the history after": git-filter-repo with `--sensitive-data-removal` (needs ≥ 2.47); command `git-filter-repo --sensitive-data-removal --invert-paths --path <file>`; rewriting has side effects | same page ("Purging a file…", "Side effects of rewriting history") | 2026-10-26 |
| "Add .env to .gitignore" (docs: "add that filename to `.gitignore`") | same page, "Avoiding accidental commits in the future" | 2026-10-26 |
| `git rm --cached` removes a path only from the index and leaves the working-tree file alone | https://git-scm.com/docs/git-rm | 2026-10-26 |
| Push protection for users is enabled by default and stops you pushing secrets to public repositories on GitHub (guide note only) | https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection | 2026-10-26 |
| GitHub Support only helps remove sensitive data when rotating credentials can't mitigate the risk (guide note only) | removing-sensitive-data page | 2026-10-26 |

## Fiction (sketch, not claims)
The forker, "thirty seconds ago", the email draft, the commit message "ship it", the key value
`a91f3c7e…`, `hunter2`, the empty `.gitignore`, "I've got this", "you also pushed node_modules" and the
"API keys" dashboard menu are invented for the scene. The dashboard is a generic recreation, not any
provider's real UI.

## Dropped
- "Bots find leaked keys within minutes": common claim, no primary source checked, not used.
- Push protection in the video: it depends on the secret type and settings; kept to one sourced note in the guide.
