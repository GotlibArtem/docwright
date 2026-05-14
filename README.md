# docs-agent

AI-powered documentation agent that watches your commits and keeps README and wiki pages up to date automatically.

## How It Works

```
Developer commits / pushes
        │
        ▼
CI runs docs-agent
        │
        ├─ First run?
        │   └─ Generates all docs from scratch via LLM
        │
        └─ Already initialized?
            ├─ No relevant changes → skips (fast)
            └─ Relevant changes → updates only affected AUTO sections
                        │
                        ▼
             Direct commit  OR  Pull Request (configurable)
```

The agent only rewrites `<!-- AUTO:section -->` blocks. Anything you write manually stays untouched.

## Quick Start

Install into any repository:

```bash
pip install docs-agent
docs-agent install
```

This asks two questions (AI provider, commit mode) and creates:
- `.docs-agent/docs-agent.yml` — config
- `Makefile` targets: `make docs`, `make docs-sync`
- CI workflow (GitHub Actions or GitLab CI)

Then generate docs for the first time:

```bash
make docs
```

After that, docs update automatically on every push.

## CLI Commands

| Command | Description |
|---------|-------------|
| `docs-agent install` | Bootstrap a repository (interactive or `--auto`) |
| `docs-agent init` | Generate all documents from scratch |
| `docs-agent run` | Update changed sections based on latest diff |
| `docs-agent sync` | Force re-sync all AUTO sections |
| `docs-agent dashboard` | Terminal table of all registered projects |
| `docs-agent report` | Generate static HTML status report |

## Configuration

`.docs-agent/docs-agent.yml`:

```yaml
provider:
  type: claude          # claude | openai | ollama
  model: claude-opus-4-7
  api_key_env: ANTHROPIC_API_KEY

output:
  mode: direct          # direct | pull_request

triggers:
  paths:
    - "src/**"
    - "app/**"
  ignore:
    - "tests/**"

documents:
  - type: readme
    template: readme/default
    target: README.md
  - type: wiki
    template: wiki/architecture
    target: docs/wiki/architecture.md
```

## Supported Providers

| Provider | When to use |
|----------|-------------|
| Claude (Anthropic) | Best output quality |
| OpenAI (GPT-4o) | Alternative if you have OpenAI keys |
| Ollama | Local model, no external API — for private projects |

## Document Templates

Built-in templates cover the full documentation surface:

| Template | AUTO sections |
|----------|---------------|
| `readme/default` | overview, getting_started, architecture, api, development |
| `wiki/architecture` | overview, components, data_flow, dependencies |
| `wiki/api-contracts` | endpoints, authentication, error_codes |
| `wiki/development-guide` | setup, testing, code_style |
| `wiki/operations` | deployment, monitoring, runbooks, incident_response |
| `wiki/data-model` | entities, business_rules, relationships |
| `wiki/db-schema` | tables, indexes, migrations |
| `wiki/integrations` | external_services, auth_credentials, data_exchange |
| `wiki/security` | access_model, sensitive_data, requirements |
| `wiki/troubleshooting` | common_issues, diagnostics, known_limitations |
| `wiki/adr` | recent_decisions, decision_index |

Custom templates go in `.docs-agent/templates/` inside your repository.

## AUTO / MANUAL Sections

```markdown
# README

<!-- AUTO:overview -->
This section is managed by docs-agent.
<!-- /AUTO:overview -->

<!-- MANUAL -->
## Contributing

Write whatever you want here — docs-agent never touches MANUAL blocks.
<!-- /MANUAL -->
```

## Central Registry

After `docs-agent init`, the project is registered in a central `registry.yml`. View all projects:

```bash
docs-agent dashboard          # terminal table
docs-agent report             # HTML page at docs-agent-report.html
```

## Development

```bash
poetry install
poetry run pytest             # 46 tests
poetry run ruff check .       # lint
poetry run mypy docs_agent    # type check
```

## License

MIT
