# Cloud setup contract

Run after the repository has been cloned:

```sh
bash scripts/setup/cloud-env-setup.sh --install-tools --install --sync-context
```

Use that command in the cloud environment's setup field. A pasted script without its
repository files cannot run. The script resolves the repository from its own location.
Run without `--install` for a read-only capability check.

The host needs Git, Python 3, Node.js and npm. With --install-tools, root Ubuntu
containers can install missing Python/Git through apt. Missing Node/npm are installed
from the official Node 22.23.2 Linux distribution (Python tar data filter required).
Other hosts must provide their core runtime. Each package root and package manager
is declared in `cloud-contract.json`; packageManager in package.json must agree when present.
Pinned pnpm installs live under `~/.local/share/cloud-setup/`, leaving global tools alone.
Locked dependencies install with lifecycle scripts disabled. Run any needed native package
build steps separately after reviewing their scripts. Setup does not claim an application
build passed. Cockpit has no package root: use the target repository's setup for product work.

`verified` means the named command actually succeeded; `unavailable` means missing or failed;
`untested` means no relevant operation was attempted. Exit 2 reports a required tool,
package-manager or dependency failure. A missing declared CLI makes the result degraded (exit 2); independent checks still run. Exit 0 is not a claim of cloud or production readiness.
Provider credentials are optional during setup. Missing values are reported as
`unavailable` without blocking agent startup. Use `--require-environment` only when
the requested task requires every environment variable declared in this contract;
then missing values also cause exit 2. Credentials are checked for presence only. Provider authentication and permissions require a
separate read-only probe. No secret values or subprocess output are printed.

This setup never reads a secrets file, copies private data, changes provider settings,
sends messages, spends money, runs migrations, or ingests financial data. Provision credentials
through the cloud environment's secret store with the scope needed by the specific task.
A vault-only token must never be reused to fetch another private repository.

After configuring setup, start a fresh cloud session and retain its setup output. Then run
relevant safe local checks and separately verify the requested live behaviour. Local execution
of this script proves local behaviour only; it does not activate a cloud environment.
The --install-tools option installs missing gh 2.100.0, gitleaks 8.30.1, Supabase
2.116.0 and Vercel 59.11.7 from upstream releases/npm on Linux x64 or arm64.
Existing CLIs are version-probed. Set the persistent cloud session PATH to include the cloned repository scripts/setup
directory first, then ~/.local/bin. The repo-aware pnpm wrapper selects the declared
version for the current working directory; installing one repository cannot switch
another repository to a different pnpm version.
They are never assumed authenticated. Browser dependencies belong to the target repo
test setup; use its hermetic test instructions, never production credentials for E2E.

Shared command context uses a local TAP checkout first, otherwise TAP_GITHUB_TOKEN
scoped to read TAP. It installs adjacent command references, brand-voice-guide,
commodity-gate, home and the home agent definitions. A vault token has no role here.
The shared commands may still require task-specific repository scripts; verify those
before running the command. --sync-context checks installed files, not every workflow.

Python projects use uv.lock with uv sync --frozen --no-install-project --no-build.
--install-tools provisions uv 0.12.9 from Astral when this contract needs it.
Native source builds and editable project installs remain separate, explicit steps.
Audio devices, Ableton bridges, local media and external drives remain untested here.

Python projects use uv.lock with uv sync --frozen --no-install-project --no-build.
--install-tools provisions uv 0.12.9 from Astral when this contract needs it.
Native source builds and editable project installs remain separate, explicit steps.
Audio devices, Ableton bridges, local media and external drives remain untested here.

Downloaded binary archives are checked against recorded upstream SHA256 digests before
extraction. Update their reviewed digests together with any version change.

The cloud-only .claude/hooks/cloud-session-path.sh SessionStart hook persists this
PATH through CLAUDE_ENV_FILE for subsequent session commands. It identifies its own
repository, shell-quotes the PATH assignment, and does nothing on the Mac. It changes
no permissions and writes no credentials. A missing cloud env-file reports unavailable.

## Browser capability in a cloud session

Check the actual session before claiming that a browser is unavailable:

```sh
node scripts/setup/cloud-browser.mjs doctor
node scripts/setup/cloud-browser.mjs render http://localhost:3000/ /tmp/app-page.png
```

Use the running app's actual port in that command.

The helper discovers Playwright in the declared package roots or pnpm store, then
uses its installed browser or a preinstalled browser cache, including the cloud
image's `/opt/pw-browsers`. No package or browser download runs. `doctor` reports
paths only: launching remains untested. `render` launches, checks the HTTP response
and saves a screenshot. Open that screenshot to inspect the visible page. A rendered
page does not prove a control works; follow the target repository's verification
workflow and drive the actual control with an assertion on the resulting behaviour.
Use hermetic test data for E2E. A tiny localhost HTML fixture proves browser capability,
not TAP behaviour. This helper does not start an app or provision its data.

`CLOUD_BROWSER=firefox` or `CLOUD_BROWSER=webkit` selects another installed engine;
`CLOUD_BROWSER_EXECUTABLE` supplies a known executable when discovery needs help.
An alternate cached executable can differ from the Playwright package's expected
version, so a launch error remains `unavailable` (exit 2), never a successful check.
The helper accepts a localhost starting URL only. The page may still load remote
assets or redirect; review the final URL and screenshot. Use the available browser
connector or an explicit Playwright script for public-site checks.

On 08 September 2026, cloud session `session_01Bf3uh7g1Bnjpp2B1HgZ4Nz` successfully
clicked a localhost HTML button, observed its DOM change and captured before/after
screenshots with preinstalled Chromium. Public Chromium browsing in that same session
failed at the browser relay with `ws_closed_mid_exchange`, although curl returned 200.
That is a transport failure, not evidence of an approval denial, and curl does not
prove browser navigation. Recheck the current session's browser and proxy helper
instructions before diagnosing it. Do not disable certificate verification or alter
permissions in response to that error. Report the precise failed route and any
separately verified route; a prior session's success is not current capability proof.
