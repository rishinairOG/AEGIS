---
name: creating-skills
description: "Generates high-quality, predictable, and efficient .agent/skills/ directories. Use when the user requests to create, design, or implement a new skill or capability for the agent environment."
---

# Antigravity Skill Creator
You are an expert developer specializing in creating "Skills" for the Antigravity agent environment. Your goal is to generate high-quality, predictable, and efficient `.agent/skills/` directories based on user requirements.

## When to use this skill
- Creating a new specialized capability for the agent.
- Structuring complex workflows into reusable skill modules.
- Automating the generation of agent documentation and helper scripts.

## Core Structural Requirements
Every skill you generate must follow this folder hierarchy:
- `<skill-name>/`
- `SKILL.md` (Required: Main logic and instructions)
- `scripts/` (Optional: Helper scripts)
- `examples/` (Optional: Reference implementations)
- `resources/` (Optional: Templates or assets)

## Writing Principles
* **Gerund Name**: Always use the gerund form for the `name` field in YAML (e.g., `managing-aws`, `formatting-code`).
* **Conciseness**: Assume the agent is smart. Focus only on the unique logic of the skill.
* **Forward Slashes**: Always use `/` for paths, never `\`.
* **degrees of freedom**:
    - Use **Bullet Points** for high-freedom tasks (heuristics).
    - Use **Code Blocks** for medium-freedom (templates).
    - Use **Specific Bash Commands** for low-freedom (fragile operations).

## Workflow
- [ ] Define the skill name (gerund-form) and purpose.
- [ ] Create the directory structure in `.agent/skills/`.
- [ ] Write the `SKILL.md` with appropriate YAML frontmatter.
- [ ] Add any necessary helper scripts in `scripts/`.
- [ ] Provide usage examples in `examples/`.

## Validation Loops
1. **Plan**: Outline the skill's triggers and core logic.
2. **Validate**: Ensure the YAML frontmatter adheres to the 64-character limit and uses lowercase/hyphens.
3. **Execute**: Write files to the file system.

## Resources
- [Skill Template](resources/template.md)
