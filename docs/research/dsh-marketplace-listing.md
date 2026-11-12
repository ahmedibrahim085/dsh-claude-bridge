# Where and how a dsh plugin is listed

Research for issue #15 (map #8). Date of the evidence: 2026-11-12. dsh installed: 0.2.2-rc.1.

Conventions: every claim cites its source. `INFERRED:` marks a claim with no executed check behind it. Paths under `$DSH` mean `~/.npm-global/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/`.

## Answer in one screen

1. **dsh has no official marketplace.** No default index ships, the Discover tab is an experimental bundle that is off by default, and the official repo takes no external pull requests. The only official discovery rule is the GitHub topic `dsh-plugin`.
2. **The community list that matters is `awesome-dsh-plugin/awesome-dsh-plugin`.** It is a community repo (not DeepSeek's) with a real contribution guide. It is also the source of a format-1 index that dsh's Discover tab can read, and the dsh-market plugin installs only from it.
3. **Our repo meets every hard requirement of that list today.** `dsh.bundle` is declared, the repo is 6 days old (bar: 1 day), it carries the `dsh-plugin` topic, and it has real code and a licence. It is not listed yet (no entry file, no open PR).
4. **Two gaps, neither blocks the list:** the `dsh.catalog` block in `package.json` is read by nothing we could find, and the npm name `dsh-claude-bridge` belongs to someone else, so we cannot appear in the Discover index (npm-only) without publishing under another name.

## 1. Every place a dsh plugin can be listed

| # | Place | What it is | Who runs it | Our status |
|---|---|---|---|---|
| A | GitHub topic `dsh-plugin` | Discovery convention named by DeepSeek | DeepSeek (convention); crawled by many lists | Done: our topics include `dsh-plugin` (`gh api repos/ahmedibrahim085/dsh-claude-bridge`) |
| B | Official in-app catalog (recommendation cards) | Embedded list of shipped, optional, official bundles | DeepSeek | Closed to third parties |
| C | Discover tab, custom plugin indexes | Reads format-1 JSON indexes that the user adds | User picks the index | Not listed in any index |
| D | `awesome-dsh-plugin/awesome-dsh-plugin` | Community list, PR per plugin, 10,688 entry files | Community maintainers | Not listed, no PR |
| E | dsh-market plugin | In-app store built on list D | `dsh-market` org | Follows D |
| F | Format-1 index `dsh-plugin-catalog` (npm) | List D rendered as a Discover index | Same maintainers as D | Not listed (needs npm package) |
| G | Other community lists and aggregators | Topic crawlers and hand-curated lists | Various | See section 5 |
| H | npm keyword search | `keywords` in `package.json` | npm | We have the keywords; no npm package under our name |
| I | Self-hosted format-1 index | Any static JSON file | Us | Optional, not built |

### A. GitHub topic `dsh-plugin`
- DeepSeek's README tells plugin authors to add it: https://github.com/deepseek-ai/deepseek-harness/blob/master/README.md (line 46: "Add the `dsh-plugin` topic to your plugin repository for discoverability"). `CONTRIBUTING.md` line 15 says the same.
- The official repo itself carries the topic (`gh api repos/deepseek-ai/deepseek-harness --jq .topics` returns `["ai-agents","cordis","dsh","dsh-plugin"]`).
- Topic-crawling lists (section 5) pick us up from it. Our repo has it.

### B. Official in-app catalog: closed
- `$DSH/dsh-plugin-recommendations/README.md:88`: "Only shipped, optional, official plugins are eligible; missing packages and third-party registries are excluded."
- `$DSH/dsh-plugin-manager/README.md:48`: on-demand catalog entries are "marked as `official`" and carry "embedded localized metadata"; the catalog is compiled into dsh, with no registry lookup.
- The official repo accepts no outside pull requests: https://github.com/deepseek-ai/deepseek-harness/blob/master/CONTRIBUTING.md (line 9: "we cannot accept external pull requests at the moment"; line 15 points plugin authors to the topic).
- Conclusion: there is no route for us into this catalog. Nothing to file.

### C. Discover tab (custom plugin indexes)
- DeepSeek's design note says (line 9): "No official market exists, and one may be added later, so a market mechanism must work with indexes that third parties publish." Source: https://github.com/deepseek-ai/deepseek-harness/blob/master/.agents/notes/implemented/feature/2026-10-02-plugin-market-index-format.md
- `$DSH/dsh-experimental-plugin-market-bundle/README.md:56`: "There is no official index; Discover lists only the index sources the user adds." The bundle is "disabled" in shipped profiles (same file, Summary).
- User guide (https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/plugin-market.md): the user switches on **Custom plugin indexes** under Experimental plugins, then adds an index URL. "DSH ships no index source."
- So "listing" here means: be inside some index JSON that users add. Index format and install rules are in section 3.

### D. awesome-dsh-plugin (the main community list)
- Repo: https://github.com/awesome-dsh-plugin/awesome-dsh-plugin (created 2026-08-13, CC0-1.0, 24,438 stars per `gh api`). Guide: https://github.com/awesome-dsh-plugin/awesome-dsh-plugin/blob/main/contributing.md. Details in section 2.
- It is not an official DeepSeek property. Its README says "A curated list of plugins for DeepSeek Harness" and its own disclaimer says listing is not a security review (contributing.md, review item 5).

### E. dsh-market
- https://github.com/dsh-market/dsh-market (created 2026-08-14, 12,169 stars). Install it with `dsh plugin --profile web add dshmarket`.
- README line 100: "Installs are restricted to sources listed in the curated awesome-dsh-plugin registry — anything else is rejected." So for dsh-market users, listing in D is the only way in.
- Themes only: entries in category `theme` appear in its Themes tab (contributing.md, "Themes & skins"). Not relevant to us.

### F. Format-1 index `dsh-plugin-catalog`
- README of D (line 13): add `https://cdn.jsdelivr.net/npm/dsh-plugin-catalog/index.json` as an index source in Discover.
- Measured: `curl -sL https://cdn.jsdelivr.net/npm/dsh-plugin-catalog/index.json` returns format 1, 23 categories, 5,437 plugins, every version `source.type = "npm"`. D has 10,688 entry files, so about half the list is not in the index.
- Why: https://github.com/awesome-dsh-plugin/awesome-dsh-plugin/blob/main/scripts/lib/market-index.mjs (lines 11-14): "an entry needs an npm package, an exact version, and that version's publish time. The GitHub-only half of the list cannot be expressed yet". Lines 116-119 skip entries with no npm record.
- Consequence for us: a GitHub-only entry is listed in D (README, website, dsh-market) but is **absent from this Discover index** until an npm package exists whose `repository` field points back at our repo (contributing.md, "npm package": the mapping "is picked up automatically from the registry", and the package's `repository` "must point back at the repository listed here").

### G. Other lists: see section 5.

### H. npm keywords
- No official rule. `package.json` `keywords` is the npm convention reused by the index format (`.agents/notes/.../plugin-market-index-format.md`, line "metadata.keywords conventionally comes from npm package.json keywords"). Discover search matches keywords (`$DSH/dsh-plugin-market/README.md`, "Text matches the package name, author, keywords...").
- We already have `dsh`, `dsh-plugin`, `deepseek-harness`, `claude-code` among our keywords. They only matter once an npm package under our name exists (see 6.3).

### I. Self-hosted index
- DeepSeek documents it and ships a reference generator: https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/plugin-market-generator/README.md. Input is a text list of npm names or https Git URLs; output is `index.json` plus `icons/`.
- For a Git repo it lists a version per tag `vX.Y.Z`, `X.Y.Z` or `<name>@X.Y.Z`, only where `package.json` at that tag declares `dsh.bundle`, is not `"private": true`, and has the same name and version as the tag. Our tags `v0.2.1` to `v0.5.0` follow `vX.Y.Z`.
- Only useful if we want our own index; it does not reach other users unless they add the URL.

## 2. awesome-dsh-plugin: how listing works

All from https://github.com/awesome-dsh-plugin/awesome-dsh-plugin/blob/main/contributing.md unless stated.

**Entry format.** One pull request adds one file `data/plugins/<owner>__<repo>.yml` (line 7 onward). READMEs are generated and must not be hand-edited.

```yaml
url: https://github.com/owner/repo
name: owner/repo
category: dev
description:
  en: One-line description ending with a period.   # only description.en is required
  zh: ...                                          # optional, maintainers add it
icon: https://raw.githubusercontent.com/owner/repo/main/assets/icon-180.png   # optional
tarball: https://github.com/owner/repo/releases/latest/download/name.tgz      # optional
```

A description containing `: ` must be quoted. A monorepo subpackage uses `owner/repo#subname` and a `tree/main/...` URL.

**Categories** (line 49): `agi ui usage theme model identity session memory tools wsl browser vision voice docs skill workflow git notify dev security remote market fun`. The set is not fixed; a maintainer changes a near-miss category instead of bouncing the PR (review item 2).

**Requirements** (lines 56-90, enforced by CI where marked):

| Requirement | CI-checked? | Source |
|---|---|---|
| `package.json` declares `dsh.bundle` (root, or a subpackage under `packages/`, `plugins/`, `apps/`). Only `dsh.client` fails. | Yes | contributing.md:58-60; `scripts/check-submission.mjs` header lines 3-5 |
| Repo is at least 1 day old (`MIN_AGE_DAYS = 1`, from the GitHub `created_at`). No commit-count bar. A repo that is too young passes by itself on a later re-run. | Yes | contributing.md:79; `check-submission.mjs:21` and 399-409 |
| Repo exists, is not archived, is not a copy of dsh's own bundle | Yes | `check-submission.mjs` header lines 7-8 |
| At most 3 entries per PR | Yes | contributing.md:148-150 |
| `awesome-lint` and the site build pass (locale parity, formatting) | Yes | contributing.md:162 onward |
| Real working code, not a placeholder or README-only repo | Maintainer reads the repo | contributing.md:56-78 and review item 3 |
| `dsh-plugin` topic on the repo | Listed as requirement; no CI check found | contributing.md |
| Actively maintained (a decay scan flags gone, archived, dormant repos and removes them after review) | Periodic scan | contributing.md:82 |
| Description states what it does, is accurate, and is checked against the code (numbers and API names must be true) | Maintainer reads the repo | contributing.md, requirements and review item 1 |
| Not a meta-package (dependency list only), and its dependencies point at the original authors | Maintainer | review items 7 and 8 |
| Licence | **Not required**. The guide names no licence rule. | contributing.md (full read) |
| `engines.dsh` | **Not required**. The guide names no rule for it. | contributing.md (full read) |

**Review process** (contributing.md, "How submissions are reviewed"). CI is the precondition, not the decision. A maintainer reads the target repository and checks: claims vs code, category, real code, duplicates, anything alarming in the source, whether the PR touches other entries, meta-package, dependency origin. Feedback comes as a PR comment. A maintainer may apply the label `held: author` to pause the PR until the author fixes and comments once. The site rebuilds after merge.

**Recommended, not required:** publish to npm (skips the build-approval step and enables download counts); attach a prebuilt tarball to a GitHub Release and set `tarball:`; declare `@deepseek-ai/*` as `peerDependencies`; add `screenshots.json` (1-8 images) beside `package.json`; an icon (GitHub-hosted png/jpg/jpeg/webp).

## 3. The format-1 index (what Discover reads)

Sources: https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/plugin-market.md and `$DSH/dsh-plugin-market-index/lib/index.js` (the executable rules, read in full).

- Root: `format: 1`, `title` (LocalizedText, needs `en`), optional `description`, `metadata.categories`, `metadata.labels`, `metadata.sortKeys`, `plugins[]`.
- Plugin: `name` (npm package name, unique), optional `title`, `description`, `icon`, `author`, `homepage`, `repository {url, directory?}`, `metadata.category`, `metadata.keywords`, `versions[]` (at least one).
- Version: `version` (exact SemVer), `publishTimestamp` (Unix seconds), `source` = `{type:"npm", registry?}` or `{type:"git", url, commit (40 hex), path?}`, optional `engines.dsh` (SemVer range).
- Categories are whatever the index declares; there is no global list. The community index declares the 23 category ids of section 2.
- Requirements on the packages: the index validator cannot check them. DeepSeek's note says generators must ensure every listed version declares `dsh.bundle` and that `engines.dsh` matches the package (note, "Generator obligations", line 176). A version with a missing, blank or invalid `engines.dsh` is refused by the generator and validator (note, Consequences, line 231).
- Review: none by DeepSeek. "DSH checks the file format but not those claims" (user guide, Browse and install). "Market text reaches users... without review by DSH" (note, Risks, line 242).
- Install target: npm `name@version`, or `git+<url>.git#<commit>` with `&path:/<dir>`. dsh checks `engines.dsh` again at install; with `engines.dsh` present it alone decides, otherwise the `@deepseek-ai/dsh*` peer ranges do (`$DSH/dsh-app-boot/README.md:52`).

## 4. How comparable integration and bridge plugins are listed

All in D, from `data/plugins/*.yml` (https://github.com/awesome-dsh-plugin/awesome-dsh-plugin/tree/main/data/plugins) and the catalog index.

| Plugin | Category | What it does | In Discover index? |
|---|---|---|---|
| `biedongbin/dsh-claude-compat` (PR 4836, merged) | `dev` | "Two-way Claude Code <-> DSH bridge": loads `.claude/` skills, hooks, `.mcp.json` into dsh, imports sessions | Yes (npm `dsh-claude-compat`, category `dev`) |
| `lidaqi001/dsh-claude-code-delegate` (PR 12541, merged) | `workflow` | Agent preset that hands tasks to a Claude Code subagent | Yes (category `workflow`) |
| `wanwulizhi/dsh-claude-code-sdk` (PR 8655, merged) | `tools` | Delegates coding tasks to local Claude Code through the Agent SDK | No |
| `zhangjunjesse/dsh-claude-driver` (PR 3396, merged) | `model` | Runs the main model on a Claude Code subscription | No |
| `wuanthony397-hash/dsh-codex-peer` | `agi` | Peer collaboration with the local Codex CLI | No |
| `patrick1099/dsh-claude-plugin-loader` | `dev` | Loads Claude-style plugins into dsh | not checked |

What the pattern shows:
- Direction matters for the category. Plugins that bring Claude Code assets into dsh sit in `dev`; plugins where dsh calls Claude Code sit in `workflow` or `tools`. Our bridge goes both ways (Claude Code drives dsh; dsh finished turns signal Claude Code), the closest precedent is `dsh-claude-compat` in `dev`.
- Entries are short factual descriptions that name the requirement ("Requires Claude Code installed and signed in").
- Only entries with an npm package reach the Discover index (rows 1 and 2). Git-only entries (rows 3-5) are listed in D but not in F.
- PR 9952 (three Dobo233 plugins) was closed, 4720 (`dsh-claude-memory`) closed; reasons were not read, so we draw no rule from them. INFERRED: closures fit the rules in section 2 (age, manifest, duplicates).

## 5. Other community lists (all third party, none official)

Checked with `gh api` (creation date, stars) and by reading their contributing files. All are open to a self-submitted repo; none has a licence or `engines.dsh` rule.

| List | Intake | Rules that apply to us |
|---|---|---|
| `bruc3van/awesome-dsh-plugin` (515 stars) | Daily crawl of the `dsh-plugin` topic, maintainer review queue; separate self-promotion lane | Public, topic, GitHub description set, installable plugin, accurate text. Self-promotion lane needs more than 10 stars (CONTRIBUTING.md). Our repo qualifies for the crawl, not the showcase |
| `dshworks/awesome-dsh-plugins` (35 stars) | PR to `data/plugins.json`, plus a topic sweep queue | A "spam gate": real install path (`dsh.bundle` manifest, npm package, or valid `SKILL.md`), not a template copy, loads on the dsh version claimed (`engines.dsh` is checked), honest own-words description. Rejections carry a recheck date |
| `kejixiaoliang/awesome-dsh-plugins` (80 stars) | PR adds one line in `plugins/<category>.md` | dsh-specific plugin, public repo, README, runnable code. Rejects "generic Claude/Codex/Cursor plugins" unless dsh support is explicit. Ours is dsh-specific |
| `billLiao/awesome-dsh-plugin` (21 stars) | PR adds one line in `categories/*.md` | `dsh-plugin` topic and `dsh.bundle` |
| `beancookie/awesome-dsh-plugin` (194 stars) | PR adds a line to both READMEs | Same rules as D's older guide: `dsh.bundle`, real code, active, topic |
| `0xsline/awesome-deepseek-harness` (1,353 stars) | Hand-curated PR | Real repo, one-line factual description. Its guide says its source index lives in a private org |
| `Alex-Yanggg/awesome-DSH-plugin` (103 stars) | PR with README line plus `catalog/plugins.json` | Plugin or documented maintained integration, public URL, install docs, bilingual description. No push since 2026-08-15 |
| `diegosouzapw/awesome-omni-dsh-plugins` (22 stars) | PR with YAML against a schema | Schema with SPDX licence, exact SemVer and SRI install pin, evidence of dsh support. Heaviest bar of the lists read. No push since 2026-10-09 |
| `hashgraph-online/awesome-ai-plugins` (1,036 stars) | PR, multi-client list with a dsh section | `dsh.bundle` and an `apply(ctx)` entry point, repo URL and install command in the README (CONTRIBUTING.md, "DeepSeek Harness submissions") |
| `AdamPlatin123/dsh-plugin-radar` (1,503 stars) | Auto-discovery from the topic and npm, plus a PR registry | Topic is enough for discovery (README line 154) |
| `unStone/dsh-xray` (8 stars) | Auto scan, no intake | Already published a capability card for our repo: https://unstone.github.io/dsh-xray/p/ahmedibrahim085__dsh-claude-bridge.html (found by `gh search code`). It rates us "C2 — one powerful capability or sensitive behavior. It patches the dsh runtime." |

Not checked: `dshplugin/dsh-plugin-hub`, `cccakeee/awesome-dsh-plugins` (no contributing file located). Lists change daily; the counts above are from 2026-11-12.

## 6. Does our manifest meet the requirements?

Ours (`package.json` at v0.5.0): `dsh.manifestVersion: 1`, `dsh.bundle.patch: ./cordis.patch.yml`, `dsh.catalog {...}`, `engines {node >=24.9.0, dsh >=0.2.2-rc.1 <0.3.0}`, `license: MIT`, `keywords` include `dsh-plugin`, no `private`, `files` lists `cordis.patch.yml`, `index.mjs`, `bin/`, `skills/`.

### 6.1 Requirements of list D: all met

| Requirement | Ours | Evidence |
|---|---|---|
| `dsh.bundle` with `patch` | Met | `package.json`; `cordis.patch.yml` exists and inserts `id: dsh-claude-bridge`, `name: 'dsh-claude-bridge'` |
| Repo at least 1 day old | Met (6 days) | `gh api repos/ahmedibrahim085/dsh-claude-bridge` returns `created_at 2026-11-06T13:44:22Z`; today is 2026-11-12 |
| `dsh-plugin` topic | Met | topics: `acp agents claude-code deepseek-harness dsh dsh-plugin mcp notifications` |
| Public repo, not archived | Met | `private: false` |
| Real code | Met | `index.mjs`, 6 bins, tests, skill |
| Not a meta-package | Met | It ships behaviour of its own |
| Install path that works | Met | `dsh plugin --profile web add github:ahmedibrahim085/dsh-claude-bridge#v0.5.0`; the entry file `index.mjs` is committed, no build step |
| Already listed under another name | Not listed | No `data/plugins/ahmedibrahim085__*` file in the 10,688 (`git/trees` listing); `gh search prs "dsh-claude-bridge"` finds no PR of ours |

### 6.2 `dsh.catalog` is not a field dsh defines

- `$DSH/dsh-package-manifest/lib/types/types.d.ts`: `DshManifest` has `manifestVersion`, `bundle`, `profile`, `client`. There is no `catalog`.
- `grep -rn --include=*.js -E "dsh\??\.catalog|\.dsh\.catalog|manifest\??\.catalog" $DSH` returns nothing; the positive control (`dsh\??\.bundle`) matches 15 files, so the search works.
- The list D scripts `scripts/lib/capabilities.mjs`, `release-manifest.mjs`, `probe-capabilities.mjs` contain no `catalog` reference.
- The listing data comes from elsewhere: Discover index display fields come from the entry file in D, or, for the reference generator, from the package's `locale/en.json` (`meta.title`, `meta.description`), else `name` and `description` (generator README, "What gets listed"). Category and capabilities are never read from `package.json`.
- INFERRED: the `dsh.catalog` block is ignored and harmless (the format ignores unknown fields at the index level; for manifests we did not run a profile load with it). It also misleads readers into thinking `category: integration` is registered anywhere; no list has a category called `integration`.

### 6.3 npm name collision blocks the Discover index

- `npm view dsh-claude-bridge name version repository.url maintainers` returns version `0.2.0`, repository `shaneconner/dsh-claude-bridge`, a "Claude Pro or Max subscription as a DeepSeek Harness model provider" plugin, published 2026-08-30. It is another person's package.
- Format-1 entries need the npm package whose `repository` points at our repo (section 1, F). Our `package.json` `name` is the same as that package. We cannot publish it.
- `npm view @ahmedibrahim085/dsh-claude-bridge` returns E404, so a scoped name is free today. INFERRED: the npm scope `@ahmedibrahim085` is controllable by us; not verified.
- Renaming affects `dsh plugin add github:...` (dsh installs a Git package by the name in its `package.json`) and the bundle id in `cordis.patch.yml`. INFERRED: needs its own ticket and a migration note; not tested here.
- Whether we want the Discover index at all is a decision for #16 (listing is optional; section 7).

### 6.4 Smaller gaps (optional)

- No `locale/en.json`, `icon` or `screenshots.json`. Only the reference generator and D's optional fields use them; `package.json` `description` is the fallback.
- `engines.dsh` is present and valid. Tested with the semver in dsh's own `node_modules`: `0.2.2-rc.1`, `0.2.2-rc.2`, `0.2.2`, `0.2.9` satisfy `>=0.2.2-rc.1 <0.3.0`; `0.2.1` and `0.2.3-rc.1` do not (the second because a prerelease tag only matches a range comparator that shares its major.minor.patch). So a future `0.2.3-rc.x` refuses our package until we raise the range. dshworks' spam gate checks this.
- `$DSH/dsh-package-manifest/README.md:96` says installers "do not enforce `engines.dsh`". That sentence is stale: `$DSH/dsh-app-boot/README.md:52` says the range "alone decides" at profile start.
- The description text for the entry must be true against the code (D reads the code). Our `package.json` summary names "turn events, wait CLI, setup/doctor for acpx, mcacp and Claude Code helpers on two brains"; each claim should be re-checked when the entry is written.

## 7. What this means for ticket #16 (not acted on)

Research only. Nothing was opened, filed or published.

- **Cheapest listing that reaches users:** one PR to `awesome-dsh-plugin/awesome-dsh-plugin` adding `data/plugins/ahmedibrahim085__dsh-claude-bridge.yml`. Draft values: `url: https://github.com/ahmedibrahim085/dsh-claude-bridge`, `name: ahmedibrahim085/dsh-claude-bridge`, `category: dev` (precedent: `dsh-claude-compat`; a maintainer may move it), a one-sentence `description.en`. That covers the website, README and dsh-market users.
- **To also appear in Discover (index F):** publish to npm under a name we own, with `repository` pointing at our repo. Decision needed: rename the package, or accept being absent from Discover.
- **Nothing to do for:** the official catalog (closed), `dsh.catalog` (ignored; keep or remove is a tidiness choice), a licence or `engines.dsh` field (both already present).
- **Reputation note:** list D's maintainers read the code. dsh-xray already rates us "patches the dsh runtime" because `cordis.patch.yml` mounts the plugin; that matches what the bundle does.

## Sources not reachable or not read

- `dsh-external/hub` (named by the `0xsline` guide) does not resolve with our `gh` login: `gh repo view dsh-external/hub` fails with "Could not resolve to a Repository". That guide says the org has been private since August 2026.
- The two closed PRs in section 4 (9952, 4720): reasons not read.
- `awesome-dsh-plugin` PR and issue history was sampled through `gh search`, not read in full.
