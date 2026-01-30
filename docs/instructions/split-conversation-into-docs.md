# Split Conversation into Ordered Documents

## Purpose
Convert helpful information from an AI conversation into a set of ordered documents with minimal redundancy, organized in a folder with a README that provides context.

## When to Use
- Conversation contains substantial information worth saving as reference
- Information has natural dependencies (concept B builds on concept A)
- You want to revisit the information later without reading the entire conversation
- Information will be useful across multiple projects or sessions

## Prerequisites
- A conversation with substantial, organized information
- A clear topic or theme for the folder name
- Understanding of what audience will read these documents

## Input Required

Ask the user:
1. **What is the core topic?** (This becomes the folder name)
2. **Who will read this?** (Affects tone and assumed knowledge)
3. **Where should documents be saved?** (If not specified, use current directory)
4. **Any specific splitting criteria?** (E.g., "split by technology," "split by phase")

## Steps

### 1. Analyze the Conversation
- Identify major topics or concepts
- Determine if topics have dependencies (A must be understood before B)
- Check if information would be redundant if documents are order-independent

### 2. Decide on Structure

**If topics have clear dependencies** (most common):
- Use numbered documents (01-, 02-, 03-, etc.)
- Order them by conceptual dependency
- README explains reading order
- Each document assumes previous ones were read

**If topics are independent**:
- Use unnumbered documents
- README lists all documents with descriptions
- Each document is self-contained (may have some redundancy)

### 3. Create Folder Name
- Use kebab-case (my-topic-name)
- Be specific but not over-specific
  - Good: `transition-guide`, `api-patterns`, `deployment-setup`
  - Bad: `docs`, `windows-to-mac-c#-to-python-ai-workflow-2026`
- Name should signal the coherent topic

### 4. Split Content

For each document:
- **Clear scope**: Each document covers one major concept or phase
- **Self-contained within dependency chain**: Don't require jumping between documents
- **Consistent structure**: Use similar headings, formatting across documents
- **Examples over theory**: Include concrete examples, code snippets, commands
- **Action-oriented**: Focus on what to do, not just concepts

Typical document count: 3-5 documents (if you have 1-2, maybe don't split; if you have 10+, consider sub-folders)

### 5. Write README.md

Include:
- **Title/topic**: One line explaining what this is
- **Reading order**: Numbered list with brief description of each document
- **Usage instructions**:
  - First-time readers: read in order
  - Returning readers: jump to specific docs
- **Context**: Any assumptions about reader's background or situation

### 6. Review for Redundancy

Check that:
- Numbered documents don't repeat context unnecessarily
- Each document references previous ones when needed ("As discussed in 01-...")
- Folder name and README provide the shared context

## Output

A folder containing:
```
topic-name/
├── README.md                 # Reading guide and context
├── 01-first-concept.md       # Foundation concepts
├── 02-second-concept.md      # Builds on 01
├── 03-third-concept.md       # Builds on 01 and 02
└── ...
```

Or for independent topics:
```
topic-name/
├── README.md                 # Lists all documents
├── concept-a.md              # Self-contained
├── concept-b.md              # Self-contained
└── ...
```

## Example

**User request**: "This conversation about transitioning from C# to Python with AI is helpful. Save it as reference."

**Analysis**:
- Topics: mindset shift, project setup, code guidelines, multi-project workflow
- Dependency: Mindset must come first, then setup, then guidelines, then workflow
- Audience: Developer transitioning from C#/Windows to Python/TypeScript/Mac
- Folder name: `transition-guide`

**Structure decision**: Ordered documents (concepts build on each other)

**Output**:
```
transition-guide/
├── README.md                          # Explains order and context
├── 01-mindset.md                      # Foundation: how to think about AI collaboration
├── 02-project-setup.md                # Builds on mindset: concrete setup steps
├── 03-code-guidelines.md              # Builds on setup: how to write code
└── 04-multi-project-workflow.md       # Builds on all: advanced workflow
```

## Tips

- **When in doubt, use numbered order**: It's easier to skip reading a document than to hunt for missing context
- **Folder name is the context**: Don't repeat it in every document title
  - Good: `auth-guide/01-setup.md`
  - Bad: `auth-guide/01-auth-setup.md`
- **README is navigation**: Think of it as a table of contents
- **Test the order**: Can document N be understood without reading N+1? Good. Can it be understood without reading N-1? If no, order is correct.

## Common Mistakes to Avoid

1. **Too many documents**: 10+ documents means you need sub-folders or the topic is too broad
2. **Too few documents**: If you only have 1-2 topics, maybe just save as a single reference file
3. **Wrong granularity**: Documents should be "chapters" not "paragraphs" or "books"
4. **Missing README**: Always include it - it's the entry point
5. **Vague folder names**: `notes`, `docs`, `stuff` - be specific about the topic
