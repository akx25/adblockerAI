"""Install a domain list as a Windows hosts-file blocker.

Usage:
	python adblockerAI.py preview
	python adblockerAI.py install
	python adblockerAI.py uninstall
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path


HOSTS_PATH = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"
DOMAINS_PATH = Path(__file__).with_name("ad-domains.txt")
BEGIN_MARKER = "# adblockerAI: begin"
END_MARKER = "# adblockerAI: end"
DOMAIN_PATTERN = re.compile(
	r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$",
	re.IGNORECASE,
)


def load_domains(path: Path) -> list[str]:
	"""Read plain domains while ignoring list metadata and comments."""
	if not path.exists():
		raise FileNotFoundError(f"Domain list not found: {path}")

	domains: set[str] = set()
	for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
		value = raw_line.strip().lower()
		if not value or value.startswith("#") or value.startswith("["):
			continue
		value = value.split()[0].rstrip(".")
		if DOMAIN_PATTERN.fullmatch(value):
			domains.add(value)
	return sorted(domains)


def remove_managed_block(hosts_text: str) -> str:
	pattern = re.compile(
		rf"\n?{re.escape(BEGIN_MARKER)}.*?{re.escape(END_MARKER)}\n?",
		re.IGNORECASE | re.DOTALL,
	)
	return pattern.sub("\n", hosts_text).rstrip() + "\n"


def install(domains: list[str]) -> None:
	if not domains:
		raise ValueError(f"No valid domains found in {DOMAINS_PATH}. Save the pasted list there first.")
	if not HOSTS_PATH.exists():
		raise FileNotFoundError(f"Windows hosts file not found: {HOSTS_PATH}")

	original = HOSTS_PATH.read_text(encoding="utf-8", errors="replace")
	backup = HOSTS_PATH.with_name("hosts.adblockerAI.backup")
	shutil.copy2(HOSTS_PATH, backup)
	cleaned = remove_managed_block(original)
	block = "\n".join([BEGIN_MARKER, *[f"0.0.0.0 {domain}" for domain in domains], END_MARKER])
	HOSTS_PATH.write_text(cleaned.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
	print(f"Installed {len(domains):,} domains.")
	print(f"Backup: {backup}")


def uninstall() -> None:
	if not HOSTS_PATH.exists():
		raise FileNotFoundError(f"Windows hosts file not found: {HOSTS_PATH}")
	current = HOSTS_PATH.read_text(encoding="utf-8", errors="replace")
	if BEGIN_MARKER.lower() not in current.lower():
		print("No adblockerAI block found.")
		return
	HOSTS_PATH.write_text(remove_managed_block(current), encoding="utf-8")
	print("Removed the adblockerAI block from the hosts file.")


def main() -> int:
	parser = argparse.ArgumentParser(description="Manage a Windows hosts-file ad blocker.")
	parser.add_argument("command", choices=("preview", "install", "uninstall"))
	args = parser.parse_args()

	try:
		if args.command == "uninstall":
			uninstall()
			return 0
		domains = load_domains(DOMAINS_PATH)
		if args.command == "preview":
			print(f"Found {len(domains):,} valid domains in {DOMAINS_PATH}")
			print("\n".join(domains[:20]))
			return 0
		install(domains)
		return 0
	except PermissionError:
		print("Access denied. Run PowerShell or Command Prompt as Administrator.", file=sys.stderr)
		return 1
	except (FileNotFoundError, OSError, ValueError) as error:
		print(error, file=sys.stderr)
		return 1


if __name__ == "__main__":
	raise SystemExit(main())


