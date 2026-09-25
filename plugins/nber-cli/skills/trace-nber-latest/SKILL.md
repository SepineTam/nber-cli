---
name: trace-nber-latest
description: "Use this skill when the user wants to track the latest NBER working papers, filter them by research topics, and generate paper recommendation posts or weekly digests in the user's language."
metadata:
    version: "0.1.0"
---

# Trace the latest NBER paper

Monitor the latest NBER working papers, filter them by the user's preset research topics, and generate paper recommendation posts in the user's language.

## When to use

Use this skill when the user wants to:

- Get the latest NBER working papers.
- Filter papers by specific research topics.
- Generate a single-paper recommendation or a weekly digest in the user's language.

## Workflow

1. **Read configuration**
   - Read `trace-nber-latest/config.toml`.
   - Research topics are in `filter.topics`.
   - The similarity threshold is in `filter.threshold`.

2. **Fetch papers**
   - Run in the terminal:
     ```bash
     uvx nber-cli feed fetch --format json
     ```
   - Add `--max-items N` if you want to limit the number of papers.
   - Parse the returned JSON and extract the `results` array.
   - For a single known paper, you can also run:
     ```bash
     uvx nber-cli info <paper-id> --format json
     ```

3. **Filter by topic**
   - For each paper's abstract, run:
     ```bash
     uv run --with requests scripts/topic-related.py "<topic>" "<abstract>"
     ```
   - You will get `similarity: 0.xxxx`.
   - If the score is greater than or equal to `filter.threshold`, the paper matches the topic.
   - The same paper may match multiple topics.

4. **Generate post copy**
   - Refer to `examples/single-paper-post.md` for single-paper recommendations.
   - Refer to `examples/weekly-paper-posts.md` for weekly digests.
   - Do not deviate from the template format.
   - Write in the user's language (the language the user is using in the conversation) with an academic and restrained tone.

5. **Output**
   - Print the generated markdown copy directly in the conversation.
   - If the user wants to save it, write to the `output/` directory (the path comes from `[output].dir` in `config.toml`).

## Output format

### Single-paper post

Use the structure from `examples/single-paper-post.md`:

```markdown
---
date: YYYYMMDD-HH:MM
command: uvx nber-cli info <paper-id> --format json
paper: <paper-id>
issue-date: YYYY-MM-DD
title: <paper-title>
authors:
    - <author-1>
    - <author-2>
topics:
    - <topic-1>
    - <topic-2>
links: <paper-url>
---

# <paper-title>

## One-liner
A one-sentence summary of the core finding.

## Abstract
The paper's abstract, kept accurate and unchanged.

## Why read it?
1-2 sentences explaining why this paper matters for the user's topics.

## Story
A plain-language explanation of what the paper does and what it finds.

### Shine point
The key methodological or conceptual contribution that makes this paper stand out.
```

### Weekly digest

Use the structure from `examples/weekly-paper-posts.md`:

```markdown
---
date: YYYYMMDD-HH:MM
command: uvx nber-cli feed fetch --format json --max-items N
results:
    - wXXXXX
    - wXXXXX
---

# NBER Weekly Paper Posts

Abstract: A short overview of the week's papers and which ones match the user's topics.

## wXXXXX

### metadata
- title: <paper-title>
- authors: <author-list>
- topics: [<topic-1>, <topic-2>]
- related-value: 0.xxx

### Why Read it?
Why this paper fits the user's interests.

### Story
Plain-language summary of the paper.

### Shine Point
What makes this paper notable.

## Other Papers This Week

- **wXXXXX <title>**: one-line summary.
```

Only papers with a similarity score above `filter.threshold` get a full section. Papers below the threshold go into "Other Papers This Week" with a one-line summary.

## Configuration

`config.toml` is a local configuration file and will not be committed to git (it is listed in `.gitignore`).
On first use, copy `config.example.toml`:

```bash
cp config.example.toml config.toml
```

Key fields:

```toml
[embedding]
base_url = "https://api.openai.com/v1"
api_env = "OPENAI_API_KEY"      # environment variable name
api_key = ""                    # or put the real key here (only in local config.toml)
model = "text-embedding-3-small"

[filter]
topics = ["labor economics", "gender", "immigration"]
threshold = 0.72                # cosine similarity threshold

[output]
dir = "./output"
```

The API key is read from the `api_key` field first. If that is empty, the script reads the environment variable specified by `api_env`.

## Notes

- Do not modify `config.example.toml`.
- Do not commit `config.toml` with a real API key to git.
- Paper titles, authors, NBER IDs, and links must be accurate. Do not rewrite them.
- The `Abstract` section should keep the original abstract unchanged.
- The `One-liner`, `Story`, and `Shine point` sections should be rewritten for readability.
- If a topic has no matching papers, state that explicitly.
