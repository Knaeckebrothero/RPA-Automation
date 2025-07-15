import os
import shutil
from dotenv import load_dotenv
from pathlib import Path


class PythonProjectCopier:
    # Files and paths to be copied (relative to repository root)
    # Can include files from any location in the repository
    CONFIG_FILES = [
        'requirements.txt',  # Files at repository root
        'setup.py',
        'pyproject.toml',
        '.env.example',
        'README.md',
        '.devcontainer/devcontainer.json',
        'table_detection.py',
        'db_init.py',
        'app_init.py',
        'email_downloader.py',
        'examples/email_templates/reminder_template.html',
        'examples/email_templates/response_template.html',
        'deployment/certificate.yml',
        'deployment/deployment.yml',
        'deployment/Dockerfile',
        'deployment/secret.yml',
        '.github/workflows/main.yml',
        '.github/workflows/tests.yml',
        '.github/workflows/trivy.yml',
        # Add any other files you want to copy (use relative paths)
    ]

    # --- New attribute ---
    # Directories to be copied entirely (relative to repository root)
    CONFIG_DIRS = [
        'tests',
        # Add any directories you want to copy entirely
    ]

    # File extensions to copy from the project
    CODE_EXTENSIONS = {'.py', '.json', '.yaml', '.yml', '.sql', '.cfg'}

    # Directories to exclude
    EXCLUDE_DIRS = {'.git', '.venv', 'venv', '__pycache__', '.idea', '.pytest_cache', 'logs'}

    # Specific files to exclude (even if they match extension criteria)
    # These files will be skipped during copying, regardless of their extension
    EXCLUDE_FILES = {
        '.env',                  # Environment variables (may contain secrets)
        'local_settings.py',     # Local configuration
        'secrets.py',            # Secrets file
        'config_local.py',       # Local config
        '.DS_Store',             # macOS system file
        'Thumbs.db',             # Windows system file
        # Add any other specific files you want to exclude
    }

    # --- New attribute ---
    STRUCTURE_FILENAME = "original_project_structure.txt"

    def __init__(self, repo_root: str, src_path: str, dest_path: str):
        self.repo_root = Path(repo_root).resolve() # Use absolute path for robustness
        self.source_path = Path(src_path)
        # Ensure source_path is relative to repo_root if it's inside, or handle absolute paths
        if not self.source_path.is_absolute():
            self.source_path = (self.repo_root / self.source_path).resolve()
        else:
            self.source_path = self.source_path.resolve()

        self.dest_path = Path(dest_path).resolve()
        self.copied_files_relative_paths = set() # Use a set to avoid duplicates automatically
        self.excluded_files_count = 0  # Track number of excluded files

    def copy_project(self):
        """
        Main method to copy the Python project and generate structure file.
        """
        print(f"Copying Python project from {self.source_path} to {self.dest_path}")
        print(f"Repository root considered: {self.repo_root}")

        # Reset collected paths for this run
        self.copied_files_relative_paths = set()
        self.excluded_files_count = 0

        # Create destination directory if it doesn't exist
        self.dest_path.mkdir(parents=True, exist_ok=True)

        # Copy configuration files
        self._copy_config_files()

        # --- New: Copy files from specified directories ---
        self._copy_config_dirs_files()

        # Copy Python source files from the specified src_path
        self._copy_source_files()

        # --- New step: Generate structure file ---
        self._generate_structure_file()

        print(f"\nProject copy completed! Files are in: {self.dest_path}")
        print(f"Original structure explanation saved to: {self.dest_path / self.STRUCTURE_FILENAME}")
        if self.excluded_files_count > 0:
            print(f"Note: {self.excluded_files_count} files were excluded based on EXCLUDE_FILES list")

    def _copy_file_with_flattened_name(self, source_file: Path):
        """
        Copies a file to the destination, creating a unique flat name.
        Checks for excluded and already copied files.
        Returns True if copied, False otherwise.
        """
        # Check if the file is in the exclude list by name
        if source_file.name in self.EXCLUDE_FILES:
            print(f"Skipping excluded file: {source_file.relative_to(self.repo_root)}")
            self.excluded_files_count += 1
            return False

        rel_path_from_repo = source_file.relative_to(self.repo_root)
        rel_path_str = str(rel_path_from_repo)

        if rel_path_str in self.copied_files_relative_paths:
            # Already copied, probably from CONFIG_FILES and now found again in source scan
            return False

        # Create a unique filename by joining the relative path parts
        unique_filename_base = "_".join(rel_path_from_repo.parts).replace(rel_path_from_repo.suffix, '')
        unique_filename = unique_filename_base + rel_path_from_repo.suffix
        dest_file = self.dest_path / unique_filename

        print(f"Copying '{rel_path_from_repo}' to '{unique_filename}'")
        try:
            shutil.copy2(source_file, dest_file)
            self.copied_files_relative_paths.add(rel_path_str)
            return True
        except Exception as e:
            print(f"Error copying {source_file} to {dest_file}: {e}")
            return False

    def _copy_config_files(self):
        """
        Copy files specified in CONFIG_FILES from anywhere in the repository.
        """
        print("\n--- Copying specified files ---")
        copied_count = 0
        for config_file_rel_str in self.CONFIG_FILES:
            source_file = self.repo_root / config_file_rel_str

            if source_file.exists() and source_file.is_file():
                if self._copy_file_with_flattened_name(source_file):
                    copied_count += 1
            else:
                print(f"Warning: File not found or is not a file: {config_file_rel_str} (looked in {source_file})")
        print(f"Finished copying specified files. Copied {copied_count} file(s).")

    # --- New Method ---
    def _copy_config_dirs_files(self):
        """
        Copy all files from directories specified in CONFIG_DIRS.
        """
        print("\n--- Copying files from specified directories ---")
        copied_count = 0
        for dir_str in self.CONFIG_DIRS:
            source_dir = self.repo_root / dir_str
            if not source_dir.is_dir():
                print(f"Warning: Directory not found, skipping: {dir_str}")
                continue

            print(f"Processing directory: {dir_str}")
            for root, dirs, files in os.walk(source_dir):
                # Exclude sub-directories
                dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]

                for file in files:
                    file_path = Path(root) / file
                    if self._copy_file_with_flattened_name(file_path):
                        copied_count += 1

        print(f"Finished copying from specified directories. Copied {copied_count} file(s).")

    def _copy_source_files(self):
        """
        Copy all relevant source files from self.source_path into a flat structure.
        """
        print(f"\n--- Copying source files (extensions: {self.CODE_EXTENSIONS}) from {self.source_path} ---")
        if not self.source_path.exists() or not self.source_path.is_dir():
            print(f"Warning: Source directory '{self.source_path}' not found or is not a directory. Skipping source file copy.")
            return

        copied_count = 0
        # Walk through the source directory
        for root, dirs, files in os.walk(self.source_path, topdown=True):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS and Path(root, d) not in self.EXCLUDE_DIRS] # Check full path too

            current_dir = Path(root)

            # Check if the current directory itself should be excluded (relative to repo_root)
            try:
                current_dir_rel_to_repo = current_dir.relative_to(self.repo_root)
                if any(part in self.EXCLUDE_DIRS for part in current_dir_rel_to_repo.parts):
                    # print(f"Skipping excluded directory: {current_dir_rel_to_repo}") # Optional debug
                    continue
            except ValueError:
                # This happens if current_dir is not inside repo_root, should not occur with resolve()
                print(f"Warning: Could not make path relative to repo root: {current_dir}")
                continue

            # Copy files with matching extensions
            for file in files:
                file_path = current_dir / file

                # Ensure it's not in an excluded dir (redundant check, but safe)
                if any(part in self.EXCLUDE_DIRS for part in file_path.relative_to(self.repo_root).parts):
                    continue

                if file_path.suffix in self.CODE_EXTENSIONS:
                    if self._copy_file_with_flattened_name(file_path):
                        copied_count += 1

        print(f"Finished copying source files. Copied {copied_count} file(s).")

    # --- New Method ---
    def _generate_structure_file(self):
        """
        Generates a text file describing the original project structure
        based on the copied files.
        """
        print(f"\n--- Generating structure file: {self.STRUCTURE_FILENAME} ---")
        structure_file_path = self.dest_path / self.STRUCTURE_FILENAME

        if not self.copied_files_relative_paths:
            print("No files were copied, skipping structure file generation.")
            return

        # Sort paths for consistent output
        sorted_paths = sorted(list(self.copied_files_relative_paths))

        # Build a tree structure (dictionary based)
        tree = {}
        for path_str in sorted_paths:
            path_parts = Path(path_str).parts
            node = tree
            for i, part in enumerate(path_parts):
                is_last_part = (i == len(path_parts) - 1)
                if is_last_part:
                    # Mark as file (using None, or could use a special marker)
                    node[part] = node.get(part) # Don't overwrite if dir exists with same name
                    if node[part] is None: # Only mark if not already a dir
                        node[part] = 'FILE'
                else:
                    # Ensure dictionary exists for directory part
                    node = node.setdefault(part, {})


        # Function to recursively format the tree
        def format_tree(node, indent=""):
            lines = []
            # Sort items: directories first, then files
            items = sorted(node.items(), key=lambda item: (0, item[0]) if isinstance(item[1], dict) else (1, item[0]))

            for name, value in items:
                prefix = "|-- "
                connector = "|   "
                if items.index((name, value)) == len(items) - 1: # Last item uses a different connector
                    prefix = "└── "
                    connector = "    "

                if isinstance(value, dict): # It's a directory
                    lines.append(f"{indent}{prefix}{name}/")
                    lines.extend(format_tree(value, indent + connector))
                elif value == 'FILE': # It's a file
                    lines.append(f"{indent}{prefix}{name}")
                # Else: Could be a file that has the same name as a directory handled earlier, ignore.
            return lines

        try:
            with open(structure_file_path, 'w', encoding='utf-8') as f:
                f.write(f"Original Project Structure (based on copied files relative to {self.repo_root.name}):\n")
                f.write(f"{self.repo_root.name}/\n") # Add the root directory name

                # Generate the tree starting from the root structure
                structure_lines = format_tree(tree, indent="    ") # Start with indentation for root content

                for line in structure_lines:
                    f.write(line + '\n')
            print(f"Successfully wrote structure to {structure_file_path}")
        except IOError as e:
            print(f"Error writing structure file: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during structure file generation: {e}")


# --- Main execution part ---
if __name__ == "__main__":
    # Load environment variables from .env file in the script's directory
    load_dotenv()

    # Get the script's directory (assuming it's the repository root for this example)
    script_dir = Path(__file__).parent.resolve()
    repo_root_path = script_dir # Modify if script is not at repo root

    # Define source path for recursive search (relative to repo root)
    # Common pattern is to have code in a 'src' or project-name directory
    src_code_path = 'src' # Modify if your source code is elsewhere

    # Get the destination path from env var or use a default relative to script dir
    copy_target_path_str = os.getenv('COPY_PATH', 'output_copy') # Default to './output_copy'
    dest_copy_path = repo_root_path / copy_target_path_str / 'extracted_python_project_files'

    print("--- Configuration ---")
    print(f"Repository Root: {repo_root_path}")
    print(f"Source Code Dir: {repo_root_path / src_code_path}")
    print(f"Destination Dir: {dest_copy_path}")
    print("---------------------\n")

    # Create and run the copier
    try:
        # Ensure repo_root and src_path are passed correctly
        copier = PythonProjectCopier(repo_root=str(repo_root_path),
                                     src_path=str(repo_root_path / src_code_path), # Pass absolute path to init
                                     dest_path=str(dest_copy_path))
        copier.copy_project()
    except Exception as e:
        print(f"\n--- An error occurred during the process ---")
        import traceback
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        print("--------------------------------------------")
