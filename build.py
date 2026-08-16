import argparse
import ast
import base64
import hashlib
import os
import re
import subprocess
import sys
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
DIST_DIR = SCRIPT_DIR / "dist"
ROOT_DIST_DIR = SCRIPT_DIR.parent.parent
SRC_DIR = SCRIPT_DIR
HEADER_FILE = SRC_DIR / "header.py"


def get_plugin_id() -> str:
    try:
        content = HEADER_FILE.read_text(encoding="utf-8")
        match = re.search(r'__id__\s*=\s*"([^"]+)"', content)
        return match.group(1) if match else "template"
    except Exception:
        return "template"


OUTPUT_FILENAME = f"{get_plugin_id()}.plugin"

PRIORITY_FILES = ["header.py"]
PRIORITY_DIRS = ["data", "i18n", "utils", "features"]
LAST_FILES = ["main.py"]

INTERNAL_MODULES = ("data", "i18n", "utils", "features", "header")

captured_imports = defaultdict(set)
captured_from_imports = defaultdict(set)

COPYRIGHT_STRING = "# Powersaver Sync plugin for exteraGram / Ayugram"

HEADER_WATERMARK = """
#          @@@@@@@@@@
#        @@@@@@@@@@@@
#       @@@@@
#       @@@@
# @@@@@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@@@@
#       @@@@
#       @@@@
#       @@@@
#       @@@@
#       @@@@
#       @@@@
# @@@@@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@@@@

# Plugin by @nonPlugins\n# https://github.com/nonFeature/sync_powersaver
"""

FOOTER_WATERMARK = """
#       @@@@
# @@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Plugin Build Script")
    parser.add_argument("--no-minify", action="store_true")
    parser.add_argument("--minify-level", choices=["light", "medium", "max"], default="max")
    parser.add_argument("--no-lint", action="store_true")
    parser.add_argument("--crlf", action="store_true")
    return parser.parse_args()


def get_current_version() -> str | None:
    content = HEADER_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else None


def run_linter():
    print("Running Ruff...")
    subprocess.run(["ruff", "check", ".", "--fix"], capture_output=True)
    subprocess.run(["ruff", "format", "."], capture_output=True)
    result = subprocess.run(["ruff", "check", "."], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Ruff issues found:\n{result.stdout}")
        return False
    print("Code is clean. Proceeding to build...")
    return True


def get_all_python_files(src: Path) -> list[Path]:
    EXCLUDE_DIRS = {".venv", "dist", "__pycache__", ".ruff_cache", ".git"}
    return [p.relative_to(src) for p in src.rglob("*.py") if p.name not in ("__init__.py", "build.py") and not any(part in EXCLUDE_DIRS for part in p.parts)]


def get_merge_order(all_files: list[Path]) -> list[Path]:
    order = []
    processed: set[Path] = set()

    for pf in PRIORITY_FILES:
        p = Path(pf)
        if p in all_files:
            order.append(p)
            processed.add(p)

    for pd in PRIORITY_DIRS:
        dir_files = sorted([f for f in all_files if f.parts[0] == pd and f not in processed])
        order.extend(dir_files)
        processed.update(dir_files)

    last_paths = {Path(f) for f in LAST_FILES}
    others = sorted([f for f in all_files if f not in processed and f not in last_paths])
    order.extend(others)
    processed.update(others)

    for lf in LAST_FILES:
        p = Path(lf)
        if p in all_files:
            order.append(p)
            processed.add(p)

    return order


def parse_import_line(line: str):
    line = line.strip()
    from_match = re.match(r"^from ([\w.]+) import (.+)$", line)
    if from_match:
        module, names = from_match.groups()
        for name in names.split(","):
            captured_from_imports[module].add(name.strip())
        return
    import_match = re.match(r"^import ([\w.]+)$", line)
    if import_match:
        module = import_match.group(1)
        _ = captured_imports[module]


def normalize_import_block(import_lines: list[str]) -> str:
    block = " ".join(line.strip() for line in import_lines)
    block = re.sub(r"#.*", "", block)
    block = re.sub(r"\s+", " ", block)
    block = block.replace("( ", "").replace("(", "").replace(" )", "").replace(")", "")
    return block.strip()


def _is_internal(mod_name):
    if not mod_name:
        return False
    return mod_name.split(".")[0] in INTERNAL_MODULES


def generate_imports_block() -> str:
    lines = []
    for mod in sorted(captured_imports.keys()):
        if _is_internal(mod):
            continue
        lines.append(f"import {mod}")
    for mod in sorted(captured_from_imports.keys()):
        if _is_internal(mod):
            continue
        names = sorted(captured_from_imports[mod])
        lines.append(f"from {mod} import {', '.join(names)}")
    return "\n".join(lines) + "\n"


def process_file_content(file_path: Path) -> list[str]:
    with open(SRC_DIR / file_path, encoding="utf-8") as f:
        lines = f.readlines()

    processed_lines = []
    in_docstring = False
    docstring_char = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not in_docstring:
            if stripped.startswith('"""'):
                docstring_char = '"""'
            elif stripped.startswith("'''"):
                docstring_char = "'''"
            else:
                docstring_char = None

        if docstring_char and docstring_char in stripped:
            count = stripped.count(docstring_char)
            if count == 1:
                in_docstring = not in_docstring
                i += 1
                continue
            elif count >= 2:
                if not in_docstring:
                    i += 1
                    continue
                else:
                    in_docstring = False
                    i += 1
                    continue

        if in_docstring:
            i += 1
            continue

        if stripped.startswith("#"):
            i += 1
            continue

        is_import = stripped.startswith(("import ", "from "))
        if is_import:
            import_lines = [line]
            open_parens = line.count("(") - line.count(")")
            while open_parens > 0 and i + 1 < len(lines):
                i += 1
                next_line = lines[i]
                import_lines.append(next_line)
                open_parens += next_line.count("(") - next_line.count(")")

            block = normalize_import_block(import_lines)
            mod_match = re.match(r"^(?:from|import)\s+([\w.]+)", block)
            mod_name = mod_match.group(1) if mod_match else ""

            if not _is_internal(mod_name):
                parse_import_line(block)
            i += 1
            continue

        processed_lines.append(line)
        i += 1

    file_code = "".join(processed_lines)
    cleaned_code = file_code.strip()
    cleaned_code = re.sub(r"\n{3,}", "\n\n", cleaned_code)
    return [cleaned_code + "\n"]


class ASTMinifier(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        node.returns = None
        for arg in node.args.posonlyargs:
            arg.annotation = None
        for arg in node.args.args:
            arg.annotation = None
        if node.args.vararg:
            node.args.vararg.annotation = None
        for arg in node.args.kwonlyargs:
            arg.annotation = None
        if node.args.kwarg:
            node.args.kwarg.annotation = None
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        node.returns = None
        for arg in node.args.posonlyargs:
            arg.annotation = None
        for arg in node.args.args:
            arg.annotation = None
        if node.args.vararg:
            node.args.vararg.annotation = None
        for arg in node.args.kwonlyargs:
            arg.annotation = None
        if node.args.kwarg:
            node.args.kwarg.annotation = None
        self.generic_visit(node)
        return node

    def visit_AnnAssign(self, node):
        self.generic_visit(node)
        if node.value is None:
            return None
        new_node = ast.Assign(targets=[node.target], value=node.value)
        return ast.copy_location(new_node, node)

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return None
        self.generic_visit(node)
        return node

    def visit_Module(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body.pop(0)
        return node

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body.pop(0)
        return node


def check_java():
    try:
        subprocess.run(["java", "-version"], check=True, capture_output=True)
        return "java"
    except Exception:
        pass

    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        java_exe = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java")
        if java_exe.exists():
            return str(java_exe)

    return None


def download_tools():
    tools_dir = SCRIPT_DIR / ".tools"
    tools_dir.mkdir(exist_ok=True)

    kotlinc_dir = tools_dir / "kotlinc"
    if not kotlinc_dir.exists():
        print("Downloading Kotlin Compiler...")
        kt_zip = tools_dir / "kotlinc.zip"
        urllib.request.urlretrieve("https://github.com/JetBrains/kotlin/releases/download/v1.9.22/kotlin-compiler-1.9.22.zip", kt_zip)
        print("Extracting Kotlin Compiler...")
        with zipfile.ZipFile(kt_zip, "r") as zip_ref:
            zip_ref.extractall(tools_dir)
        kt_zip.unlink()

    d8_jar = tools_dir / "d8.jar"
    if not d8_jar.exists():
        print("Downloading D8 (R8) compiler...")
        urllib.request.urlretrieve("https://dl.google.com/dl/android/maven2/com/android/tools/r8/8.2.33/r8-8.2.33.jar", d8_jar)

    android_jar = tools_dir / "android.jar"
    if not android_jar.exists():
        print("Downloading android.jar (API 33)...")
        urllib.request.urlretrieve("https://raw.githubusercontent.com/Sable/android-platforms/master/android-33/android.jar", android_jar)


def compile_kotlin_to_dex():
    kt_dir = SCRIPT_DIR / "kotlin"
    if not kt_dir.exists():
        return True

    kt_files = list(kt_dir.glob("*.kt"))
    if not kt_files:
        return True

    build_dir = SCRIPT_DIR / "build"
    build_dir.mkdir(exist_ok=True)
    hash_file = build_dir / "kt_hash.txt"
    constants_file = SCRIPT_DIR / "data" / "constants.py"

    current_hash = hashlib.md5(b"".join(f.read_bytes() for f in sorted(kt_files))).hexdigest()
    if hash_file.exists() and constants_file.exists():
        if hash_file.read_text(encoding="utf-8").strip() == current_hash:
            print("Kotlin files unchanged. Skipping compilation.")
            return True

    java_exe = check_java()
    if not java_exe:
        print("Java is not installed or not in PATH. Cannot compile Kotlin.")
        return False

    download_tools()

    tools_dir = SCRIPT_DIR / ".tools"
    kotlinc_bin = tools_dir / "kotlinc" / "bin" / ("kotlinc.bat" if os.name == "nt" else "kotlinc")
    android_jar = tools_dir / "android.jar"
    d8_jar = tools_dir / "d8.jar"

    print("Compiling Kotlin sources...")
    jar_path = build_dir / "classes.jar"
    kt_files_str = [str(p) for p in kt_files]

    cmd_kotlinc = [str(kotlinc_bin), *kt_files_str, "-d", str(jar_path), "-classpath", str(android_jar)]

    try:
        subprocess.run(cmd_kotlinc, check=True)
    except Exception as e:
        print(f"Failed to compile Kotlin: {e}")
        return False

    print("Converting to DEX...")
    cmd_d8 = [java_exe, "-cp", str(d8_jar), "com.android.tools.r8.D8", str(jar_path), "--output", str(build_dir), "--lib", str(android_jar)]
    try:
        subprocess.run(cmd_d8, check=True)
    except Exception as e:
        print(f"Failed to run d8: {e}")
        return False

    dex_path = build_dir / "classes.dex"
    if not dex_path.exists():
        print("classes.dex not found!")
        return False

    with open(dex_path, "rb") as f:
        dex_b64 = base64.b64encode(f.read()).decode("utf-8")

    constants_file = SCRIPT_DIR / "data" / "constants.py"
    constants_file.parent.mkdir(exist_ok=True)
    with open(constants_file, "w", encoding="utf-8") as f:
        f.write(f'DEX_B64 = "{dex_b64}"  # noqa: E501\n')

    hash_file.write_text(current_hash, encoding="utf-8")

    print("Injected DEX into constants.py.")
    return True


def build():
    args = parse_args()

    if not compile_kotlin_to_dex():
        sys.exit(1)

    if not HEADER_FILE.exists():
        print(f"Header file '{HEADER_FILE}' not found!")
        sys.exit(1)

    current_version = get_current_version()
    if not current_version:
        print("Can't find __version__ field in header!")
        sys.exit(1)

    print(f"Building {OUTPUT_FILENAME} (version: {current_version})...")

    if not args.no_lint:
        if not run_linter():
            sys.exit(1)

    all_files = get_all_python_files(SRC_DIR)
    merge_order = get_merge_order(all_files)

    body_content = []
    for file_path in merge_order:
        print(f"  Merging: {file_path}")
        body_content.append(f"\n# === {file_path} ===\n")
        body_content.extend(process_file_content(file_path))

    imports_block = generate_imports_block()
    combined_code = imports_block + "".join(body_content)

    if args.no_minify:
        print("Minification disabled via --no-minify")
        full_code = combined_code
    else:
        level = args.minify_level
        print(f"Minifying plugin (level: {level})...")

        if level == "light":
            try:
                tree = ast.parse(combined_code)
                minifier = ASTMinifier()
                minified_tree = minifier.visit(tree)
                full_code = ast.unparse(minified_tree)
            except Exception:
                full_code = combined_code
        else:
            rename_locals = level == "max"
            hoist_literals = level == "max"
            try:
                import python_minifier

                full_code = python_minifier.minify(
                    combined_code,
                    rename_globals=False,
                    rename_locals=rename_locals,
                    hoist_literals=hoist_literals,
                    remove_annotations=True,
                    remove_pass=True,
                    remove_literal_statements=True,
                    combine_imports=True,
                )
            except Exception:
                try:
                    tree = ast.parse(combined_code)
                    minifier = ASTMinifier()
                    minified_tree = minifier.visit(tree)
                    full_code = ast.unparse(minified_tree)
                except Exception:
                    full_code = combined_code

    full_code = HEADER_WATERMARK + "\n" + COPYRIGHT_STRING + "\n" + full_code + "\n\n" + FOOTER_WATERMARK

    newline = "\r\n" if args.crlf else "\n"
    DIST_DIR.mkdir(exist_ok=True)
    out_path = DIST_DIR / OUTPUT_FILENAME
    out_path.write_text(full_code, encoding="utf-8", newline=newline)

    try:
        ROOT_DIST_DIR.mkdir(exist_ok=True)
        (ROOT_DIST_DIR / OUTPUT_FILENAME).write_text(full_code, encoding="utf-8", newline=newline)
    except Exception:
        pass

    orig_bytes = combined_code.replace("\n", newline).encode("utf-8")
    orig_size = len(orig_bytes)
    final_size = out_path.stat().st_size
    saved_bytes = orig_size - final_size
    pct = (saved_bytes / orig_size) * 100 if orig_size > 0 else 0

    print(f"\nBuild successful: {out_path}")
    print(f"Size on disk: {final_size / 1024:.1f} KB (originally {orig_size / 1024:.1f} KB, saved {saved_bytes / 1024:.1f} KB / {pct:.1f}%)")


if __name__ == "__main__":
    build()
