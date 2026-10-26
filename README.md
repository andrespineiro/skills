# skills

Personal agent skills. The [skills CLI](https://github.com/vercel-labs/skills) discovers each skill in `skills/<name>/SKILL.md`.

## Skills

| Skill | Use when |
| --- | --- |
| `writing-pr` | You write or edit a pull request title or body. |
| `no-mistakes` | You run the no-mistakes gate, or you ship or validate changes. |
| `qa` | You report bugs in a QA session and file GitHub issues. |
| `write-a-skill` | You create or build a new skill. |
| `principle-fix-root-causes` | You debug and must fix the root cause. |

## Install

From a project:

```bash
npx skills add andrespineiro/skills
```

List skills. Do not install them:

```bash
npx skills add andrespineiro/skills --list
```

Install one skill for every project:

```bash
npx skills add andrespineiro/skills --skill writing-pr -g -y
```

This repository is private. The CLI uses your GitHub login to read it.

## Add a skill

1. Create `skills/<name>/SKILL.md`.
2. Set `name` to the directory name. Use lowercase letters, numbers, and hyphens.
3. Set `description` to what the skill does and when to use it.
4. Commit and push to `main`.
