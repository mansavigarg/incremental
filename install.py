import io
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlopen

base = Path.cwd()
url = "https://github.com/ryash14/loanserve-project/releases/download/v1.0.3/"

for name, archive_name in [
    ("Project", "LoanServe-project-v1.0.3.zip"),
    ("LoanServeApp", "LoanServeApp.zip"),
]:
    target = base / name
    if name == "LoanServeApp" and target.exists():
        print(f"Keeping {target}")
        continue

    with tempfile.TemporaryDirectory(dir=base) as temp:
        with urlopen(url + archive_name) as response:
            with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
                archive.extractall(temp)

        extracted = (
            next(Path(temp).rglob("run.sh")).parent
            if name == "Project" else Path(temp) / "LoanServeApp"
        )
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(extracted), target)
        print(f"Installed {target}")