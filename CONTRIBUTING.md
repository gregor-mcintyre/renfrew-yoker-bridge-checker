# Contributing

This project uses the **Git Flow** branching model, where each branch has a unique
purpose ([see below](#branch-structure)).

Code conventions - naming, docstrings, testing and commit-message style - live in
[CLAUDE.md](CLAUDE.md). Setup and test commands live in [README.md](README.md).

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
Release branch prefix: [release/]
Hotfix branch prefix: [hotfix/]
Support branch prefix: [support/]
Version tag prefix: []
```

---

## Branch Structure

| Branch      | Purpose                                                                                                                                           |
|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| `main`      | Production-ready code only. Every commit here is deployable and typically tagged with a release version.                                          |
| `develop`   | The integration branch for ongoing work. All finished features land here before a release is released.                                            |
| `feature/*` | Short-lived branches for individual features, backlog items, or bug work. Branched from and merged back into `develop`.                           |
| `release/*` | Created when preparing a new version. Used for final stabilisation, version bumps, and release-only fixes. Merged into both `main` and `develop`. |
| `hotfix/*`  | Urgent, isolated fixes for production issues. Branched from `main`, merged into both `main` and `develop`.                                        |

---

## Workflow

### Feature Branches

Use for new features.

```
# Create a new feature
git flow feature start <feature-name>

# Publish it so it is visible to others
git flow feature publish <feature-name>

# Or pull another feature
git flow feature pull origin <feature-name>

# Commit and push as you go
git commit -m "Add feature description"
git push

# Finish the feature (merges into develop and deletes the feature branch)
git flow feature finish <feature-name>
git push
```

### Release Branches

Use when preparing a new version for deployment. A release branch can bundle one or more
completed features.

```
# Create a new release
git flow release start <0.1.2>

# Publish it so it is visible to others
git flow release publish <0.1.2>

# Make any last-minute release fixes directly on the release branch
git commit -m "Final fixes for release v0.1.2"
git push

# Finish the release (merges into main and develop, and tags the release)
# Resolve any merge conflicts before pushing anything
git flow release finish <0.1.2> -m "Release v0.1.2"

# A finished release lands in three places - push all three.
# `git push --tags` pushes tags only, so main still needs its own push.
git checkout develop
git push

git checkout main
git push

git push --tags
```

### Hotfix Branches

Use for urgent production fixes.

```
# Create a hotfix from main
git flow hotfix start <hotfix-name>

# Publish it so it is visible to others
git flow hotfix publish <hotfix-name>

# Or pull another hotfix
git pull origin hotfix/<hotfix-name>

# Commit and push as you go
git commit -m "Fix critical issue"
git push

# Finish the hotfix (merges into main and develop, and tags the release)
# Resolve any merge conflicts before pushing anything
git flow hotfix finish <hotfix-name> -m "Hotfix v0.1.2"

# A finished hotfix lands in three places - push all three.
# `git push --tags` pushes tags only, so main still needs its own push.
git checkout develop
git push

git checkout main
git push

git push --tags
```

---

## More Information

- [Branching Model](https://endjin.com/blog/a-step-by-step-guide-to-using-gitflow-with-teamcity-part-2-gitflow-a-branching-model-for-a-release-cycle)
- [A successful Git branching model](http://nvie.com/posts/a-successful-git-branching-model/)
