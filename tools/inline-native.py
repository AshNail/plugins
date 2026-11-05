import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://raw.githubusercontent.com/AshNail/plugins/main/plugins/"


def sections(text):
    result = {}
    current = None
    for line in text.splitlines():
        if re.fullmatch(r"\[[^\]]+\]", line.strip()):
            current = line.strip()[1:-1]
            if current in result:
                raise ValueError("duplicate section")
            result[current] = []
        elif current and line.strip() and not line.lstrip().startswith("#"):
            result[current].append(line.strip())
    return result


def merge(profile, plugin, slug):
    if slug not in ("taobao", "adfilter"):
        raise ValueError("module not approved")
    source = sections(plugin)
    if any(lines for key, lines in source.items() if key not in ("Host", "Rule")):
        raise ValueError("only Host and Rule modules are supported")
    target = sections(profile)
    additions = {}
    for key, lines in source.items():
        if not lines:
            continue
        if key not in target:
            raise ValueError("missing destination section")
        existing = target[key]
        additions[key] = []
        for line in lines:
            if line in existing:
                continue
            if key == "Host":
                name, sep, value = line.partition("=")
                if not sep or value.strip() != "127.0.0.1":
                    raise ValueError("only loopback Host entries are supported")
                if any(x.split("=", 1)[0].strip().lower() == name.strip().lower() for x in existing):
                    raise ValueError("Host conflict")
            else:
                fields = [x.strip() for x in line.split(",")]
                if len(fields) != 3 or fields[0] not in ("DOMAIN", "DOMAIN-SUFFIX") or fields[2] != "REJECT":
                    raise ValueError("only domain REJECT rules are supported")
            additions[key].append(line)
    for key, lines in additions.items():
        if not lines:
            continue
        if key == "Rule":
            finals = list(re.finditer(r"(?m)^FINAL,[^\r\n]+$", profile))
            if len(finals) != 1:
                raise ValueError("expected one FINAL")
            pos = finals[0].start()
            profile = profile[:pos] + "\n".join(lines) + "\n" + profile[pos:]
        else:
            profile = profile.replace("[Host]\n", "[Host]\n" + "\n".join(lines) + "\n", 1)
    url = BASE + slug + "/" + slug + ".plugin"
    profile = "\n".join(line for line in profile.splitlines() if line.split(",", 1)[0].strip() != url) + "\n"
    return profile


def main():
    parser = argparse.ArgumentParser(description="Preview native module inlining; does not write private profiles")
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    original = args.profile.read_text()
    result = original
    for slug in ("taobao", "adfilter"):
        result = merge(result, (ROOT / "plugins" / slug / (slug + ".plugin")).read_text(), slug)
    before, after = sections(original), sections(result)
    for section in ("Host", "Rule", "Plugin"):
        print(section, len(before.get(section, [])), "->", len(after.get(section, [])))
    print("Preview only; no credentials printed and no file written")


if __name__ == "__main__":
    main()
