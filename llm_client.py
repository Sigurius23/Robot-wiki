"""
llm_client.py — LLM provider abstraction and note generation.

Responsibilities:
  - Provider initialisation (Anthropic / OpenAI)
  - Prompt construction from PROMPT_A_TEMPLATE and PROMPT_B_TEMPLATE
  - LLM API calls (Pass 1: paper profile, Pass 2: crossref note)
  - Output file writing with UTF-8 encoding

PROMPT_A_TEMPLATE and PROMPT_B_TEMPLATE are defined as module-level string
constants. They contain the full prompt text derived from:
  - references/schemas/entities.yaml  (Pass 1 frontmatter structure)
  - references/schemas/edges.yaml     (Pass 2 edge-type vocabulary)
  - references/templates/paper_template.md  (Pass 1 section skeleton)
"""

import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Prompt templates (placeholders — see module docstring)
# ---------------------------------------------------------------------------

PROMPT_A_TEMPLATE: str = (
    "You are an expert academic librarian responsible for distilling raw research papers "
    "into highly structured Obsidian Markdown notes. Your goal is to construct a concise, "
    "factual summary and generate YAML frontmatter that strictly adheres to the `papers` "
    "entity schema. Quality and accuracy are paramount: ensure the summary is rigorous and "
    "directly reflects the paper's actual contents. Use only the provided JSON metadata to "
    "populate frontmatter fields like year, venue, and citation counts—do NOT hallucinate "
    "or guess any data. Rely exclusively on the provided text and metadata for your output."
)

PROMPT_B_TEMPLATE: str = (
    "You are a meticulous research assistant tasked with mapping new literature against a "
    "set of 12 predefined thesis implementation decisions. Your goal is to analyze the "
    "provided paper text and determine how it impacts each decision, using the exact "
    "cross-reference edge vocabulary established in the `edges.yaml` schema. Quality "
    "expectations are high: your analysis must be brief, precise, and logically sound. You "
    "must select from the exact edge types provided below without inventing new relationships "
    "or hallucinating evidence. Base your entire analysis solely on the provided paper data."
)

# ---------------------------------------------------------------------------
# System prompts (used in _call_llm)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_A: str = (
    "You are an academic librarian formatting an Obsidian note. "
    "You MUST use the provided JSON metadata (year, venue, citations) "
    "for the YAML frontmatter. Do not hallucinate citation counts."
)

_SYSTEM_PROMPT_B: str = (
    "You are a research assistant mapping a paper against a set of "
    "predefined implementation decisions. Use only the edge type "
    "vocabulary provided in the prompt. Do not invent relationship types."
)


# ---------------------------------------------------------------------------
# Client initialisation
# ---------------------------------------------------------------------------

def init_llm_client(provider: str, api_key: str):
    """
    Initialise and return the appropriate SDK client.

    Supports Anthropic and OpenAI (case-insensitive provider name).
    Exits the process with code 1 if ``api_key`` is empty or falsy.

    Args:
        provider: ``"anthropic"`` or ``"openai"`` (case-insensitive).
        api_key:  API key string for the chosen provider.

    Returns:
        An initialised SDK client instance.

    Raises:
        SystemExit: if ``api_key`` is empty, or if ``provider`` is unknown.
    """
    provider_lower = provider.lower()

    if provider_lower not in ("anthropic", "openai"):
        print(
            f"Error: Unknown LLM provider '{provider}'. "
            f"Must be 'anthropic' or 'openai'.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not api_key:
        env_var = _env_var_for_provider(provider)
        print(
            f"Error: {env_var} is required but not set.",
            file=sys.stderr,
        )
        sys.exit(1)

    if provider_lower == "anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=api_key)

    # provider_lower == "openai"
    import openai
    return openai.OpenAI(api_key=api_key)


def _env_var_for_provider(provider: str) -> str:
    """Return the canonical environment variable name for a provider."""
    mapping = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    return mapping.get(provider.lower(), "LLM_API_KEY")


# ---------------------------------------------------------------------------
# LLM call dispatch
# ---------------------------------------------------------------------------

def _call_llm(
    client,
    provider: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Dispatch a prompt to the appropriate LLM SDK and return the response text.

    Args:
        client:        An initialised Anthropic or OpenAI client.
        provider:      ``"anthropic"`` or ``"openai"`` (case-insensitive).
        system_prompt: System-level instruction for the model.
        user_prompt:   User-level prompt text (may include the template).

    Returns:
        The model's text response.

    Raises:
        Exception: on SDK / API error (caught by the caller).
    """
    provider_lower = provider.lower()

    if provider_lower == "anthropic":
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    elif provider_lower == "openai":
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    else:
        raise ValueError(f"Unsupported provider: {provider}")


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------

def _write_output(path: str, content: str, cite_key: str) -> None:
    """
    Write *content* to *path* with UTF-8 encoding.

    Creates parent directories if they do not exist.  Prints a warning to
    stderr if the file already exists (overwrite).  Prints the OS error to
    stderr and skips the write on ``OSError``.

    Args:
        path:     Destination file path (relative or absolute).
        content:  UTF-8 string to write.
        cite_key: Cite-key (currently unused but reserved for future logging).
    """
    output_path = Path(path)

    if output_path.exists():
        print(
            f"Warning: Overwriting existing file: {path}",
            file=sys.stderr,
        )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        print(
            f"Error writing to {path}: {exc}",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Pass 1 — Paper profile note
# ---------------------------------------------------------------------------

def generate_paper_profile(
    client,
    provider: str,
    cite_key: str,
    metadata: dict,
    pdf_text: str,
) -> None:
    """
    LLM Pass 1: generate the paper profile Obsidian note.

    Constructs a prompt from ``PROMPT_A_TEMPLATE`` with *metadata* and
    *pdf_text* injected, then calls the LLM.  Writes the result to
    ``./wiki/papers/{cite_key}.md`` via ``_write_output``.

    Prints to stderr and skips the file write on API error or empty response.

    Args:
        client:    Initialised LLM SDK client.
        provider:  ``"anthropic"`` or ``"openai"`` (case-insensitive).
        cite_key:  Obsidian cite-key for the paper (e.g. ``"smith2024"``).
        metadata:  Dict with keys ``year``, ``venue``, ``citationCount``,
                   ``authors``, ``baseline_trust_score``, ``cite_key``,
                   ``title`` (some may be ``None``).
        pdf_text:  Full cleaned PDF text.
    """
    user_prompt = _build_prompt_a(metadata, pdf_text)

    try:
        response_text = _call_llm(client, provider, _SYSTEM_PROMPT_A, user_prompt)
    except Exception as exc:
        print(
            f"Error generating paper profile for '{cite_key}': {exc}",
            file=sys.stderr,
        )
        return

    if not response_text or not response_text.strip():
        print(
            f"Warning: Empty response from LLM for paper profile '{cite_key}'.",
            file=sys.stderr,
        )
        return

    output_path = f"./wiki/papers/{cite_key}.md"
    _write_output(output_path, response_text, cite_key)


def _build_prompt_a(metadata: dict, pdf_text: str) -> str:
    """Construct the Pass 1 user prompt around PROMPT_A_TEMPLATE."""

    # Build a JSON-safe subset of metadata for the prompt.
    prompt_meta = {
        "year": metadata.get("year"),
        "venue": metadata.get("venue"),
        "citationCount": metadata.get("citationCount"),
        "authors": metadata.get("authors", []),
        "baseline_trust_score": metadata.get("baseline_trust_score"),
        "cite_key": metadata.get("cite_key"),
        "title": metadata.get("title"),
    }
    meta_json = json.dumps(prompt_meta, indent=2, default=str)

    return (
        f"{PROMPT_A_TEMPLATE}\n\n"
        f"## Paper metadata (JSON)\n\n"
        f"```json\n{meta_json}\n```\n\n"
        f"## Paper full text\n\n"
        f"{pdf_text}\n\n"
        f"---\n\n"
        f"Using the metadata above, generate a structured Obsidian Markdown note "
        f"for this paper. The YAML frontmatter MUST conform to the `papers` entity "
        f"schema: include fields `title`, `venue`, `year`, `importance` (1–5), "
        f"`contribution_type`, `tags`, `cited_by`, `datasets`, `code_url`, and any "
        f"other relevant fields. Use the provided metadata values — do NOT "
        f"hallucinate citation counts or venue names. Then, follow this section "
        f"structure for the body:\n\n"
        f"## Problem & Context\n"
        f"## Key idea\n"
        f"## Method\n"
        f"## Experiment & Results\n"
        f"## Limitations\n"
        f"## Open questions\n"
        f"## My take\n"
        f"## Related"
    )


# ---------------------------------------------------------------------------
# Pass 2 — Implementation decision crossref note
# ---------------------------------------------------------------------------

def generate_crossref_note(
    client,
    provider: str,
    cite_key: str,
    pdf_text: str,
    paper_title: str,
) -> None:
    """
    LLM Pass 2: generate the implementation-decision cross-reference note.

    Constructs a prompt from ``PROMPT_B_TEMPLATE`` with *cite_key*,
    *paper_title*, and *pdf_text* injected, then calls the LLM.  Writes the
    result to ``./wiki/implementation-decisions/{cite_key}-crossref.md`` via
    ``_write_output``.

    Prints to stderr and skips the file write on API error or empty response.

    Args:
        client:       Initialised LLM SDK client.
        provider:     ``"anthropic"`` or ``"openai"`` (case-insensitive).
        cite_key:     Obsidian cite-key for the paper.
        pdf_text:     Full cleaned PDF text.
        paper_title:  Paper title (from metadata or PDF extraction).
    """
    user_prompt = _build_prompt_b(cite_key, paper_title, pdf_text)

    try:
        response_text = _call_llm(client, provider, _SYSTEM_PROMPT_B, user_prompt)
    except Exception as exc:
        print(
            f"Error generating crossref note for '{cite_key}': {exc}",
            file=sys.stderr,
        )
        return

    if not response_text or not response_text.strip():
        print(
            f"Warning: Empty response from LLM for crossref note '{cite_key}'.",
            file=sys.stderr,
        )
        return

    output_path = f"./wiki/implementation-decisions/{cite_key}-crossref.md"
    _write_output(output_path, response_text, cite_key)


def _build_prompt_b(cite_key: str, paper_title: str, pdf_text: str) -> str:
    """Construct the Pass 2 user prompt around PROMPT_B_TEMPLATE."""
    return (
        f"{PROMPT_B_TEMPLATE}\n\n"
        f"## Paper reference\n\n"
        f"- **Cite key:** {cite_key}\n"
        f"- **Title:** {paper_title}\n\n"
        f"## Edge type vocabulary\n\n"
        f"When tagging each implementation decision, you MUST use EXACTLY one of "
        f"the following relationship types:\n\n"
        f"- `supports` — the paper provides evidence or arguments in favour of "
        f"the decision\n"
        f"- `contradicts` — the paper provides evidence or arguments against "
        f"the decision\n"
        f"- `builds_on` — the paper extends, improves, or directly builds upon "
        f"the decision\n"
        f"- `challenges` — the paper questions the assumptions or validity of "
        f"the decision\n"
        f"- `addresses_gap` — the paper fills a gap that the decision identifies "
        f"or implies\n"
        f"- `no_coverage` — the paper does not meaningfully address the decision\n\n"
        f"## Paper full text\n\n"
        f"{pdf_text}\n\n"
        f"---\n\n"
        f"For each of the 12 thesis implementation decisions, write a short "
        f"analysis of how the paper relates to the decision. Tag each entry "
        f"with exactly one of the six edge types above. Format each entry as:\n\n"
        f"### Decision N: [Decision name]\n"
        f"- **Relationship:** `edge_type`\n"
        f"- **Analysis:** [1–3 sentences explaining the relationship]"
    )
