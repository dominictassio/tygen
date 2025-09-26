import csv
from pathlib import Path
import shutil
import subprocess
import tarfile

import requests
from tqdm import tqdm


def main():
    results: list[tuple[str, str, int, str]] = []

    tarballs = list(Path("tarballs").glob("*.tgz"))[:75:3]
    # tarballs = [Path("tarballs/@babel~core-7.28.4.tgz")]
    for tarpath in tqdm(tarballs):
        with tarfile.open(tarpath, "r:*") as tarball:
            package = tarpath.stem
            run_kwargs = {
                "capture_output": True,
                "cwd": f"packages/{package}/package",
                "env": {"npm_confg_loglevel": "silent"},
            }

            # step 1a. extract tarball
            tarball.extractall(f"packages/{package}", filter="fully_trusted")

            run_kwargs["cwd"] = list((Path("packages") / package).iterdir())[0]

            # step 2. install dependencies
            npm_install = subprocess.run(
                ["npm", "install", "--omit=dev", "--ignore-scripts", "--no-audit"],
                **run_kwargs,
            )
            if npm_install.stderr:
                results.append(
                    (package, "INSTALL_DEPENDENCIES", 2, npm_install.stderr.decode())
                )
                continue

            npm_ls = subprocess.run(
                ["npm", "ls", "--all", "--parseable", "--omit=dev"],
                capture_output=True,
                cwd=f"packages/{package}/package",
                env={"npm_config_loglevel": "silent"},
            )
            if npm_ls.stderr:
                results.append(
                    (package, "LIST_DEPENDENCIES", 2, npm_install.stderr.decode())
                )
                continue

            # step 2a. install types
            for line in tqdm(npm_ls.stdout.splitlines()[1:], leave=False):
                dependency = line.split(b"node_modules/")[-1]
                escaped_name = dependency.removeprefix(b"@").replace(b"/", b"__")
                definitely_typed = b"@types/" + escaped_name
                request = requests.head(
                    f"https://registry.npmjs.org/{definitely_typed.decode()}"
                )
                if request.status_code != 200:
                    continue
                npm_install = subprocess.run(
                    [
                        "npm",
                        "install",
                        definitely_typed,
                        "--omit=dev",
                        "--ignore-scripts",
                        "--no-audit",
                    ],
                    **run_kwargs,
                )
                if npm_install.stderr:
                    results.append(
                        (package, "INSTALL_TYPES", 2, npm_install.stderr.decode())
                    )
                    continue
            npm_install = subprocess.run(
                [
                    "npm",
                    "install",
                    "@types/node",
                    "--omit=dev",
                    "--ignore-scripts",
                    "--no-audit",
                ],
                **run_kwargs,
            )
            if npm_install.stderr:
                results.append(
                    (package, "INSTALL_TYPES", 2, npm_install.stderr.decode())
                )
                continue

            shutil.copy("tsconfig.json", f"packages/{package}/package")

            # step 3. run tsc
            tsc_gen = subprocess.run(
                ["tsc"],
                capture_output=True,
                cwd=f"packages/{package}/package",
            )

            for line in tsc_gen.stderr.splitlines():
                results.append((package, "GENERATE_TYPES", 2, line.decode()))

            for line in tsc_gen.stdout.splitlines():
                results.append((package, "GENERATE_TYPES", 1, line.decode()))

    with open("results/results.csv", "w", newline="") as resultsfile:
        resultscsv = csv.writer(resultsfile)
        resultscsv.writerow(("package", "category", "file", "message"))
        resultscsv.writerows(results)


if __name__ == "__main__":
    main()
