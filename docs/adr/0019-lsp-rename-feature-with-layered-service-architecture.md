# 19. LSP rename feature with layered service architecture

Date: 2026-04-26

## Status

Accepted

Related to [18. Unified output formatter with protocol-based dispatch](0018-unified-output-formatter-with-protocol-based-dispatch.md)

## Context

Workspace-wide symbol renaming is a critical LSP feature for LLM-assisted code refactoring. The CLI needs to support `textDocument/prepareRename` and `textDocument/rename` with safe defaults: preview changes before applying, atomic rollback on failure, and consistent output formatting across all formats (JSON/YAML/CSV/TEXT).

Key constraints:
- Default to dry-run mode; explicit `--apply` required for modifications
- Atomic rollback capability for failed rename operations
- Integration with existing `OutputDispatcher` and `FormattableRecord` Protocol
- Text edits only; file create/rename/delete operations deferred
- Semi-deterministic session IDs for recovery without daemon dependency

## Decision

Implement a layered service architecture with clear dependency boundaries following Clean Architecture principles.

**Layer Boundaries:**
- **CLI Layer** (outer): Typer command handling, argument parsing, user messaging
- **Domain Services Layer** (inner): `RenameService` orchestrates flow; `BackupManager` handles atomic backup/restore
- **Infrastructure Layer** (outer): LSP client for server communication; filesystem for backup storage
- **Output Layer** (outer): `RenameEditRecord` implements `FormattableRecord` Protocol; `OutputDispatcher` routes to formatters

**Invariants:**
- Domain services never depend on CLI frameworks or output formatting
- All file modifications are backed up before application
- Session IDs are semi-deterministic (hash-based) for self-contained recovery
- Edits are applied bottom-up per file to avoid offset shifts
- `prepareRename` is conditional based on server capabilities; warn but proceed if unsupported

**Rejected alternatives:**

- **Git-based rollback**
  - Pros: Uses existing version control
  - Cons: Fails when git not initialized; pollutes commit history; concurrent modifications unpredictable
  - Why not: Backup-and-restore handles all filesystem states without git dependency

- **Daemon-tracked sessions**
  - Pros: Centralized session management; richer metadata
  - Cons: Adds operational complexity; session loss on daemon restart
  - Why not: Semi-deterministic hash+timestamp achieves recovery without daemon coupling

- **Apply-by-default with --dry-run flag**
  - Pros: Fewer keystrokes for confident users
  - Cons: Risky for LLM agents; accidental modifications likely
  - Why not: Explicit opt-in (`--apply`) prevents unintended changes in automated workflows

- **Full WorkspaceEdit support (file operations)**
  - Pros: Complete LSP compliance
  - Cons: Complex cross-file renames; YAGNI for current use cases
  - Why not: TextDocumentEdit covers 95% of rename scenarios; file ops can be added later

## Consequences

**Positive:**
- Clear separation of concerns: CLI handles UX, services handle policy, infrastructure handles I/O
- Testable domain logic without CLI or LSP server dependencies
- Consistent output formatting via existing Protocol-based dispatcher
- Atomic rollback prevents partial rename corruption
- Session recovery works without running daemon

**Negative:**
- Additional complexity: backup directory management, session manifest files
- Record type must implement 4 format methods (Protocol requirement)
- Slight storage overhead for backup files until cleanup

**Risks:**
- Concurrent modifications to same files between backup and apply (mitigate: file locking or modification-time checks)
- Backup directory growth if cleanup fails (mitigate: periodic janitorial task)
- LSP client coupling in RenameService (mitigate: treat client as port; ensure transport details stay inside client)

**Interfaces:**
- `RenameService.preview(client, file, line, col, new_name) -> list[RenameEditRecord]`
- `RenameService.apply(client, file, line, col, new_name) -> tuple[list[RenameEditRecord], RenameSession]`
- `RenameService.rollback(session_id) -> None`
- `BackupManager.create_session(workspace, file, position, new_name) -> RenameSession`
- `RenameEditRecord` implements `FormattableRecord` with `to_compact_dict()`, `get_csv_headers()`, `get_csv_row()`, `get_text_line()`
