# resumegen-mcp

The MCP companion for the [resumegen](https://github.com/dev-in-f/resumegen) CLI tool. This is intended to be a single-user server and runs locally with STDIO transport. Disclaimer, I've only tested this using Claude Desktop.

## Installation

You can install `resumegen-mcp` via Docker:

```bash
docker run --rm -it dev-in-f/resumegen-mcp
```

## Configuration

You can configure the server with environment variables.

| Variable                       | Default                    | Description                                   |
| ------------------------------ | -------------------------- | --------------------------------------------- |
| `RESUMEGEN_DATA_DIR`           | `/data`                    | The workspace directory for resumegen data    |
| `RESUMEGEN_MASTER_DATA_PATH`   | `/data/master-resume.yaml` | Path to the master resume YAML file           |
| `RESUMEGEN_TAILORED_YAML_PATH` | `/data/tailored/`          | Directory to save tailored resume YAML files  |
| `RESUMEGEN_CONFIG_PATH`        |                            | Path to the resumegen configuration YAML file |

## Usage

### Available Tools

- `get_master_resume_data`: Retrieve the master resume data (the only source of truth for tailoring)
- `list_files`: List workspace files: name (relative), size, modified time
- `read_file`: Read a text file (YAML/JSON/HTML). For PDFs use `preview_resume`
- `render_resume`: Render `ResumeData` to an accessible PDF in the workspace
- `save_tailored_yaml`: Save the tailored resume data to the designated YAML path
- `preview_resume`: Render one PDF page as an image to check layout

### Available Resources

- `resumegen://schema/resume-data`: The JSON schema for `ResumeData`
- `resumegen://master-resume-data`: The master resume data in YAML format

## Using with Claude

You can use the `resumegen-mcp` server with Claude Desktop by adding the following to your `claude_desktop_config.json` file:

```json
  "mcpServers": {
    "resumegen": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v",
        "/your/data/dir:/data",
        "dev-in-f/resumegen-mcp:latest"
      ]
    }
  }
```
