"""Create an extract-in-place project ZIP without local caches or secrets."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'dist' / 'LoanServe-project.zip'
DIRECTORIES = ('artifacts', 'config', 'data', 'database', 'loanserve',
               'loanserve_question', 'output', 'processed_data', 'scripts', 'tests')
FILES = ('README.md', '.env.example', 'requirements.txt', 'tests.py', 'run.sh')


def include(path):
    return not any(part in {'__pycache__', '.pytest_cache', 'logs'} for part in path.parts) \
        and path.suffix not in {'.pyc', '.pyo'} \
        and path.name not in {'assistant_threads.sqlite', 'api_applications.db', 'llm_cache.json'}


def package():
    DESTINATION.parent.mkdir(exist_ok=True)
    with ZipFile(DESTINATION, 'w', compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for name in FILES:
            archive.write(ROOT / name, name)
        archive.writestr('.env', 'GEMINI_API_KEY=\nGEMINI_MODEL=\n')
        for directory in DIRECTORIES:
            for path in sorted((ROOT / directory).rglob('*')):
                if path.is_file() and include(path.relative_to(ROOT)):
                    archive.write(path, path.relative_to(ROOT))
    return DESTINATION


if __name__ == '__main__':
    print(package())
