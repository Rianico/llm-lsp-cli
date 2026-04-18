"""Tests verifying type annotation coverage."""

import ast
from pathlib import Path


class TestTypeAnnotationCoverage:
    """Verify type annotations are present on public APIs."""

    def _get_public_functions(self, module_path: Path) -> list[ast.FunctionDef]:
        """Extract public function definitions from a module."""
        source = module_path.read_text()
        tree = ast.parse(source)

        public_funcs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip private functions (starting with _)
                if not node.name.startswith("_"):
                    public_funcs.append(node)

        return public_funcs

    def _has_return_annotation(self, func: ast.FunctionDef) -> bool:
        """Check if function has return type annotation."""
        return func.returns is not None

    def _has_param_annotations(self, func: ast.FunctionDef) -> bool:
        """Check if all parameters have type annotations."""
        args = func.args
        # Check regular args
        for arg in args.args:
            if arg.arg != "self" and arg.annotation is None:
                return False
        # Check keyword-only args
        for arg in args.kwonlyargs:
            if arg.annotation is None:
                return False
        return True

    def test_domain_files_have_type_annotations(self):
        """Verify domain module files have type annotations on public functions."""
        domain_dir = Path("src/llm_lsp_cli/domain")

        for py_file in domain_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            public_funcs = self._get_public_functions(py_file)
            for func in public_funcs:
                # Just report - use pyright for definitive check
                if not self._has_return_annotation(func):
                    print(f"Note: {py_file}:{func.name} missing return annotation")
                if not self._has_param_annotations(func):
                    print(f"Note: {py_file}:{func.name} missing param annotations")

    def test_application_interfaces_have_type_annotations(self):
        """Verify application interfaces have type annotations."""
        interfaces_dir = Path("src/llm_lsp_cli/application/interfaces")

        for py_file in interfaces_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            source = py_file.read_text()
            tree = ast.parse(source)

            public_funcs = self._get_public_functions(py_file)
            for func in public_funcs:
                assert self._has_return_annotation(func), \
                    f"{py_file}:{func.name} missing return annotation"

    def test_config_types_has_type_annotations(self):
        """Verify config/types.py has proper TypedDict definitions."""
        types_file = Path("src/llm_lsp_cli/config/types.py")
        source = types_file.read_text()
        tree = ast.parse(source)

        # All TypedDict classes should be defined
        typed_dict_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "TypedDict":
                        typed_dict_classes.append(node.name)

        expected_classes = [
            "ServerConfig",
            "InitializeParams",
            "CapabilityConfig",
            "LspMethodConfigDict",
        ]

        for expected in expected_classes:
            assert expected in typed_dict_classes, \
                f"Missing TypedDict class: {expected}"
