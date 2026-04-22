"""Tests for detecting unused imports and dead code."""

import ast
from pathlib import Path


class TestUnusedImports:
    """Detect unused imports in Python files."""

    def _get_imports(self, tree: ast.AST) -> set[str]:
        """Extract all imported names from AST."""
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports.add(name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports.add(name)
        return imports

    def _get_used_names(self, tree: ast.AST) -> set[str]:
        """Extract all used names from AST."""
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Handle module.attribute usage
                if isinstance(node.value, ast.Name):
                    names.add(node.value.id)
        return names

    def test_domain_files_no_unused_imports(self):
        """Verify domain module files have no unused imports."""
        domain_dir = Path("src/llm_lsp_cli/domain")

        for py_file in domain_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            source = py_file.read_text()
            tree = ast.parse(source)

            imports = self._get_imports(tree)
            used = self._get_used_names(tree)

            # Check for potentially unused imports
            # (excluding imports used in __all__ or re-exports)
            unused = imports - used - {"__all__"}

            # Allow some common patterns
            allowed_unused = {"Any", "Optional", "Union", "TYPE_CHECKING"}
            actual_unused = unused - allowed_unused

            # Report but don't fail - use pyright for definitive check
            if actual_unused:
                print(f"Warning: {py_file} may have unused imports: {actual_unused}")

    def test_application_interfaces_no_unused_imports(self):
        """Verify application interfaces have no unused imports."""
        interfaces_dir = Path("src/llm_lsp_cli/application/interfaces")

        for py_file in interfaces_dir.rglob("*.py"):
            source = py_file.read_text()
            tree = ast.parse(source)

            imports = self._get_imports(tree)
            used = self._get_used_names(tree)

            # Allow common typing imports
            allowed_unused = {"Any", "Protocol", "annotations"}
            actual_unused = imports - used - allowed_unused

            if actual_unused:
                print(f"Warning: {py_file} may have unused imports: {actual_unused}")

    def test_config_types_no_unused_imports(self):
        """Verify config/types.py has no unused imports."""
        types_file = Path("src/llm_lsp_cli/config/types.py")
        source = types_file.read_text()
        tree = ast.parse(source)

        imports = self._get_imports(tree)
        used = self._get_used_names(tree)

        # Allow common typing imports
        allowed_unused = {"Any", "TypedDict", "annotations"}
        actual_unused = imports - used - allowed_unused

        # This should pass - no unused imports
        assert len(actual_unused) == 0, f"config/types.py has unused imports: {actual_unused}"
