"""Centralized constants for viber."""

from __future__ import annotations

# Generic tokens and separators
TOKEN_GROUP_PREFIX = "g"
TOKEN_PROJECT_PREFIX = "p"
TOKEN_TASK_PREFIX = "t"
ASSIGNMENT_KEY_SEPARATOR = "-"

# CLI args and startup
ARG_HELP_LONG = "--help"
ARG_HELP_SHORT = "-h"
ARG_DATA = "--data"
ARG_CHECK = "--check"
CLI_USAGE = """\
Usage: viber --data <path> [--check <path>]

Options:
  --data <path>    Path to JSON state file (required).
                   Accepts absolute paths, ~ (home), or @ (app root).
  --check <path>   Optional path for HTML check output files.
                   HTML is regenerated after each mutation.
  --help           Show this help message and exit.

Path examples:
  viber --data ~/viber/data.json
  viber --data ~/viber/data.json --check ~/viber/check.html
"""
CLI_HELP_HINT = "Run 'viber --help' for usage."
STDERR_LOAD_ERROR_PREFIX = "Error loading data file: "
STDERR_HTML_WARN_PREFIX = "Warning: Could not generate HTML check pages: "
STDERR_FATAL_PREFIX = "Fatal error: "
STDERR_ERROR_PREFIX = "Error: "

# REPL command model
PROMPT = "> "
BANNER_LINES = (
    "Viber — cross-project maintenance tracker",
    "Type 'help' for commands. Type 'exit' or 'quit' to leave.",
)
FULL_COMMANDS = frozenset({
    "create", "read", "update", "delete", "view",
    "ok", "nah", "work", "help", "exit", "quit",
})
ALIASES = {
    "c": "create",
    "r": "read",
    "u": "update",
    "d": "delete",
    "v": "view",
    "o": "ok",
    "n": "nah",
    "w": "work",
}
COMMAND_EXIT = "exit"
COMMAND_QUIT = "quit"
VERB_OK = "ok"
VERB_NAH = "nah"
COMMAND_CANCEL_CONFIRM = "y"
COMMAND_CANCEL_CONFIRM_LONG = "yes"
READLINE_BIND_ENABLE_KEYPAD = "set enable-keypad on"
READLINE_BIND_EMACS = "set editing-mode emacs"
REPL_HISTORY_SUFFIX = ".history"

REPL_HELP_TEXT = """\
Viber — cross-project maintenance tracker

Commands (full-word / alias):
  create group <name>                             c g <name>
  create project <name> g<ID>                     c p <name> g<ID>
  create task <description> [g<ID>]               c t <description> [g<ID>]

  read groups                                     r groups
  read projects                                   r projects
  read tasks                                      r tasks
  read g<ID>                                      r g<ID>
  read p<ID>                                      r p<ID>
  read t<ID>                                      r t<ID>

  update g<ID> <new-name>                         u g<ID> <new-name>
  update p<ID> name <new-name>                    u p<ID> name <new-name>
  update p<ID> state <active|suspended|deprecated> u p<ID> state <state>
  update p<ID> <active|suspended|deprecated>      u p<ID> <state>
  update t<ID> <new-description>                  u t<ID> <new-description>
  update p<ID> t<ID> [comment]                    u p<ID> t<ID> [comment]
  update t<ID> p<ID> [comment]                    u t<ID> p<ID> [comment]

  delete g<ID>                                    d g<ID>
  delete p<ID>                                    d p<ID>
  delete t<ID>                                    d t<ID>

  view                                            v       (all pending)
  view p<ID>                                      v p<ID> (pending tasks for project)
  view t<ID>                                      v t<ID> (pending projects for task)

  ok p<ID> t<ID>                                  o p<ID> t<ID>
  ok t<ID> p<ID>                                  o t<ID> p<ID>
  nah p<ID> t<ID>                                 n p<ID> t<ID>

  work p<ID>                                      w p<ID> (iterate pending tasks)
  work t<ID>                                      w t<ID> (iterate pending projects)

  help
  exit | quit"""

# Domain value strings
PROJECT_STATE_ACTIVE = "active"
PROJECT_STATE_SUSPENDED = "suspended"
PROJECT_STATE_DEPRECATED = "deprecated"
ASSIGNMENT_STATUS_PENDING = "pending"
ASSIGNMENT_STATUS_OK = "ok"
ASSIGNMENT_STATUS_NAH = "nah"

# Time formatting
UTC_SUFFIX_Z = "Z"
UTC_OFFSET_ZERO = "+00:00"
LOCAL_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_PART_SEPARATOR = " "
DATE_PART_INDEX = 0

# Generic output labels
LABEL_ALL_GROUPS = "all groups"
LABEL_GROUP_NOT_FOUND = "g{group_id} (not found)"

# Renderer constants
HTML_DEFAULT_SUFFIX = ".html"
HTML_STATUS_SYMBOL_OK = "✅"
HTML_STATUS_SYMBOL_NAH = "❌"
# Keep pending visually neutral and unobtrusive in tables.
HTML_STATUS_SYMBOL_PENDING = "&nbsp;"
HTML_DOC_TYPE = "<!DOCTYPE html>"
HTML_LANG = "en"
HTML_META_CHARSET = "UTF-8"
HTML_TITLE_PREFIX = "Viber Check — "
HTML_STYLE_LINES = (
    "    body { font-family: sans-serif; font-size: 14px; }",
    "    table { border-collapse: collapse; }",
    "    th, td { border: 1px solid #ccc; padding: 4px 8px;"
    " text-align: center; vertical-align: top; }",
    "    th { background: #f5f5f5; font-weight: bold; }",
    "    td.task-desc { text-align: left; max-width: 300px; word-break: break-word; }",
    "    td.gap { background: #ccc; }",
    "    td.pending { }",
    "    td.ok { }",
    "    td.nah { }",
)
HTML_TAG_HTML_OPEN = "<html lang=\"en\">"
HTML_TAG_HEAD_OPEN = "<head>"
HTML_TAG_HEAD_CLOSE = "</head>"
HTML_TAG_BODY_OPEN = "<body>"
HTML_TAG_BODY_CLOSE = "</body>"
HTML_TAG_HTML_CLOSE = "</html>"
HTML_TABLE_OPEN = "  <table>"
HTML_TABLE_CLOSE = "  </table>"
HTML_THEAD_OPEN = "    <thead>"
HTML_THEAD_CLOSE = "    </thead>"
HTML_TBODY_OPEN = "    <tbody>"
HTML_TBODY_CLOSE = "    </tbody>"
HTML_ROW_OPEN = "      <tr>"
HTML_ROW_CLOSE = "      </tr>"
HTML_COL_TASK = "        <th>Task</th>"
HTML_COL_CREATED = "        <th>Created</th>"
HTML_EMPTY_GROUP_TEXT = "  <p>No projects or tasks in this group.</p>"
