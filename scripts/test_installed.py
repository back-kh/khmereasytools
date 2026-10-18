"""Test a built wheel in fresh environments, outside the source checkout."""
import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import textwrap
import venv
from pathlib import Path


def check(wheel, extras, tests, report_directory):
    with tempfile.TemporaryDirectory(prefix="ket-installed-") as directory:
        environment = Path(directory) / "environment"
        venv.create(str(environment), with_pip=True)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        requirement = str(wheel) + ("[all]" if extras else "")
        subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
        command = [str(python), "-m", "pip", "install"]
        if not extras:
            command.append("--no-deps")
        subprocess.run(command + [requirement], check=True)
        subprocess.run([str(python), "-m", "pip", "check"], check=True)
        subprocess.run([str(python), "-m", "khmereasytools", "--version"], cwd=directory, check=True)
        script = textwrap.dedent('''
            import importlib.metadata
            import inspect
            import json
            import os
            import platform
            import subprocess
            import sys
            import unittest
            from pathlib import Path
            import khmereasytools as ket
            installed = Path(ket.__file__).resolve()
            assert Path(sys.prefix).resolve() in installed.parents, str(installed)
            suite = unittest.defaultTestLoader.discover(sys.argv[1])
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            versions = {}
            for name in ('khmereasytools', 'khmer-nltk', 'sklearn-crfsuite', 'python-crfsuite',
                         'scikit-learn', 'Pillow', 'pytesseract', 'pypdfium2'):
                try:
                    versions[name] = importlib.metadata.version(name)
                except importlib.metadata.PackageNotFoundError:
                    pass
            report = dict(platform=platform.platform(), python=platform.python_version(),
                          package_path=str(installed), versions=versions,
                          functions=[name for name in ket.__all__ if inspect.isfunction(getattr(ket, name))],
                          tests=result.testsRun, skipped=len(result.skipped),
                          failures=len(result.failures), errors=len(result.errors),
                          real_ocr=os.environ.get('KET_RUN_OCR_TESTS') == '1',
                          real_pos=os.environ.get('KET_RUN_POS_TESTS') == '1',
                          live_translation=os.environ.get('KET_RUN_TRANSLATION_TESTS') == '1')
            Path(sys.argv[2]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')
            sys.exit(0 if result.wasSuccessful() else 1)
        ''')
        environment_variables = dict(os.environ)
        environment_variables["PYTHONUTF8"] = "1"
        environment_variables["KET_RUN_OCR_TESTS"] = "1" if extras else "0"
        environment_variables["KET_RUN_POS_TESTS"] = "1" if extras else "0"
        environment_variables["KET_RUN_TRANSLATION_TESTS"] = "0"
        # Prove the core install is independent even if the outer runner has
        # optional packages. Only this fresh venv provides importable packages.
        report_path = report_directory / ("{}-{}.json".format(platform.system().lower(), "extras" if extras else "core"))
        subprocess.run([str(python), "-c", script, str(tests), str(report_path)],
                       cwd=directory, env=environment_variables, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--reports", type=Path, default=Path("validation-results"))
    args = parser.parse_args()
    wheels = sorted(args.dist.resolve().glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected exactly one built wheel")
    reports = args.reports.resolve()
    reports.mkdir(parents=True, exist_ok=True)
    tests = Path(__file__).resolve().parents[1] / "tests"
    check(wheels[0], False, tests, reports)
    check(wheels[0], True, tests, reports)


if __name__ == "__main__":
    main()
