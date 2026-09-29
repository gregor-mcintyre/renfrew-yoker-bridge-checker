# Contributing

This project uses the **Git Flow** branching model, where each branch has a unique
purpose ([see below](#branch-structure)).

Code conventions live in [CLAUDE.md](CLAUDE.md), the master file. Test conventions and
test commands live in [tests/CLAUDE.md](tests/CLAUDE.md), which overrides the master
file for code under `tests/`. Setup lives in [README.md](README.md), and commit messages
follow [the format below](#commit-messages).

---

## Installing Git Flow

Follow the official installation guide for your platform:
[git-flow installation instructions](https://github.com/nvie/gitflow/wiki/Installation)

Verify the install:

```bash
git flow version
```

## Initialising Git Flow

From the root of the repository, run:

```bash
git flow init
```

You'll be prompted to name each branch type. **Accept the defaults** for consistency
with the rest of the team:

```
Branch name for production releases: [main]
Branch name for "next release" development: [develop]
Feature branch prefix: [feature/]
Bugfix branch prefix: [bugfix/]
Release branch prefix: [release/]
Hotfix branch prefix: [hotfix/]
Support branch prefix: [support/]
Version tag prefix: []
```

---

## Branch Structure

| Branch      | Purpose                                                                                                                                                                     |
|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `main`      | Production-ready code only. Every commit here is deployable and typically tagged with a release version.                                                                    |
| `develop`   | The integration branch for ongoing work. Finished features and bugfixes land here before they are released.                                                                 |
| `feature/*` | Short-lived branches for new or changed behaviour, and any work that isn't a fix: refactors, docs, tooling. Branched from and merged back into `develop`.                   |
| `bugfix/*`  | Short-lived branches for bug fixes that don't justify interrupting production with a hotfix. Branched from and merged back into `develop`, same as a feature.               |
| `release/*` | Created when preparing a new version. Used for final stabilisation, version bumps, and release-only fixes. Merged into both `main` and `develop`.                           |
| `hotfix/*`  | Urgent, isolated fixes for production issues. Branched from `main`, merged into both `main` and `develop`.                                                                  |
| `support/*` | A long-term maintenance line for an old release still in use after `main` has moved on. Branched from that release's tag; never merged back — there is no `support finish`. |

---

## Workflow

### Feature Branches

Use for new or changed behaviour, and any work that isn't a fix.

```
# Create a new feature
git flow feature start <feature-name>

# Publish it so it is visible to others
git flow feature publish <feature-name>

# Or pull another feature
git flow feature pull origin <feature-name>

# Commit and push as you go
git commit -m "feat(<scope>): <what it adds>"
git push

# Finish the feature (merges into develop and deletes the feature branch)
git flow feature finish <feature-name>
git push
```

### Bugfix Branches

Use for bug fixes that aren't urgent enough to interrupt production with a hotfix.

```
# Create a new bugfix
git flow bugfix start <bugfix-name>

# Publish it so it is visible to others
git flow bugfix publish <bugfix-name>

# Or pull another bugfix
git flow bugfix pull origin <bugfix-name>

# Commit and push as you go
git commit -m "fix(<scope>): <what it corrects>"
git push

# Finish the bugfix (merges into develop and deletes the bugfix branch)
git flow bugfix finish <bugfix-name>
git push
```

### Release Branches

Use when preparing a new version for deployment. A release branch can bundle one or more
completed features and bugfixes; finish each into `develop` before starting the release.

```
# Create a new release
git flow release start <0.1.2>

# Publish it so it is visible to others
git flow release publish <0.1.2>

# Make any last-minute release fixes directly on the release branch
git commit -m "fix(<scope>): <what it corrects>"
git push

# Finish the release (merges into main and develop, and tags the release)
# Resolve any merge conflicts before pushing anything
git flow release finish <0.1.2> -m "chore(release): <0.1.2>"

# A finished release lands in three places - push all three.
# `git push --tags` pushes tags only, so main still needs its own push.
git checkout develop
git push

git checkout main
git push

git push --tags
```

### Hotfix Branches

Use for urgent production fixes. The hotfix branch name is the version being patched -
git flow tags the release from it directly.

```
# Create a hotfix from main
git flow hotfix start <0.1.2>

# Publish it so it is visible to others
git flow hotfix publish <0.1.2>

# Or pull another hotfix
git pull origin hotfix/<0.1.2>

# Commit and push as you go
git commit -m "fix(<scope>): <what it corrects>"
git push

# Finish the hotfix (merges into main and develop, and tags the release)
# Resolve any merge conflicts before pushing anything
git flow hotfix finish <0.1.2> -m "chore(release): <0.1.2>"

# A finished hotfix lands in three places - push all three.
# `git push --tags` pushes tags only, so main still needs its own push.
git checkout develop
git push

git checkout main
git push

git push --tags
```

### Support Branches

Use to keep patching an old release after `main` has moved on - someone is still running
v0.1.x, but `main` is already at v0.2.0.

Unlike the other three, a support branch is never finished or merged back into `main` or
`develop` - `git flow support` has no `finish` command. It's also the one branch type
where the base isn't optional: name the tag you're extending explicitly.

```
# Create a support branch from the release it maintains
git flow support start <0.1.x> <0.1.2>

# From here, commit, tag and push by hand - there's no `support finish` to do it:
git commit -m "fix(<scope>): <what it corrects>"
git tag -a <0.1.3> -m "chore(release): <0.1.3>"
git push origin support/<0.1.x>
git push origin --tags
```

---

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), with the
Angular type set:

```
<type>(<scope>)!: <subject>

<body>

<footers>
```

- **Type** — what the commit does for a reader of the history: `feat`, `fix`, `perf`,
  `refactor`, `test`, `docs`, `style`, `build`, `ci`, `chore` or `revert`.
- **Scope** — the top-level package or module changed, as spelt in the code. Omit it for
  a change that cuts across the codebase.
- **Subject** — imperative and lowercase, no full stop; the whole header 72 characters
  at most.
- **Body** — why, not how, in three lines at most. Leave it out when the header says it
  all, except for `feat`, `fix`, `perf`, `refactor` and `revert`.
- **Breaking change** — `!` before the colon and a `BREAKING-CHANGE:` footer.
- **Release** — the version bump is one commit, `chore(release): <version>`, and the tag
  message is the same line.

---

## More Information

- [Branching Model](https://endjin.com/blog/a-step-by-step-guide-to-using-gitflow-with-teamcity-part-2-gitflow-a-branching-model-for-a-release-cycle)
- [A successful Git branching model](http://nvie.com/posts/a-successful-git-branching-model/)
