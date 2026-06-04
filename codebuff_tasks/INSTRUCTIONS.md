# Agent Instructions: Processing Ingestion Tasks

This guide provides step-by-step instructions for a workspace agent (like Codebuff) to process the task files generated in the `codebuff_tasks/` folder and generate the final Obsidian wiki entries.

---

## Task Overview

When the ingestion pipeline runs with the `--provider codebuff` flag, it extracts the PDF text, fetches metadata, and writes the prompts and raw content to task files in `codebuff_tasks/`:
1. `{cite_key}--paper_profile.json` (Pass 1)
2. `{cite_key}--crossref_note.json` (Pass 2)

Your job is to read each of these files, perform the analysis using the prompts and PDF text enclosed, and write the output markdown files to their target paths.

---

## Step-by-Step Processing Pipeline

For each `*.json` file in `./codebuff_tasks/`:

### 1. Read and Parse the Task JSON
Load the JSON file and extract the following properties:
* `cite_key`: The unique identifier for the paper.
* `task_type`: Either `"paper_profile"` or `"crossref_note"`.
* `output_path`: The target file path for the output markdown.
* `system_prompt`: The instructions guiding the layout and format of the output.
* `user_prompt`: The prompt containing the paper metadata and truncated PDF text.
* `pdf_text`: The full, untruncated text of the paper. Use this rather than the truncated text in `user_prompt` for a higher-fidelity analysis.

### 2. Formulate the LLM Prompt
* **System Prompt**: Use the `system_prompt` from the JSON.
* **User Prompt**: Use the `user_prompt` from the JSON, but optionally substitute the truncated paper text with the full `pdf_text` to extract richer methodology details, compute statistics, and tool specifications.

### 3. Generate Output & Format Guidelines

#### For `paper_profile` Tasks:
* Follow the structure requested in the system/user prompts exactly.
* Begin the response directly with the YAML frontmatter block (`---`).
* **Do NOT use markdown code blocks (e.g., ` ```markdown ` or ` ``` `) to wrap the output.** Start directly with `---`.
* Do not add any preamble (e.g., "Here is the paper profile:") or postscript.

#### For `crossref_note` Tasks:
* Map the paper against the 12 implementation decisions defined in the prompt.
* For each decision, specify:
  - `covered`: yes / partially / no
  - `finding`: [one-sentence paraphrase + in-text citation]
  - `alignment`: aligned / contradicts / extends / not covered
* Output only the crossref note directly (no markdown wrapping fences, no preamble).

### 4. Write to Output Path
* Create parent directories for the `output_path` if they do not exist.
* Write the generated text (UTF-8 encoded) to `output_path`.
* If a file already exists at `output_path`, overwrite it.

### 5. Cleanup
* Once the markdown file is successfully written, delete the task JSON file from `./codebuff_tasks/` (or move it to a `./codebuff_tasks/completed/` directory) to avoid reprocessing it on subsequent runs.

---

## Processing Script / Command

If you want to automate this process in Python, you can use the following pattern:

```python
import os
import json
from pathlib import Path

# Iterate through tasks
task_dir = Path("./codebuff_tasks")
for task_file in sorted(task_dir.glob("*.json")):
    with open(task_file, "r", encoding="utf-8") as f:
        task = json.load(f)
        
    print(f"Processing {task['cite_key']} ({task['task_type']}) -> {task['output_path']}")
    
    # 1. Call LLM using task['system_prompt'] and task['user_prompt'] (substituting full pdf_text if needed)
    # 2. Extract output
    # 3. Create target directory
    Path(task['output_path']).parent.mkdir(parents=True, exist_ok=True)
    # 4. Write output file
    # 5. Delete or move task_file
```
