#!/usr/bin/env python

# I am using this script to obfuscate test API responses (doing it manually is too much work)

import hashlib
import json
import pathlib
import re
import sys
import typing

BIN_DIR = pathlib.Path(__file__).parent.resolve()

# Fixed prefixes to prevent double obfuscation
FAKE_UUID_PREFIX = "0bf4"
FAKE_MAC_PREFIX = "0B-F4"

WORDS = json.load((BIN_DIR / "obfuscate-data.json").open())


def hexdigest(input: str):
    return hashlib.sha1(input.encode("utf8")).hexdigest()


def generate_obfuscated_words(input: str, sep: str = " "):
    OBF_PREFIX = f"obf-word{sep}"
    if input.startswith(OBF_PREFIX):
        return input
    adjectives = WORDS["adjectives"]
    nouns = WORDS["nouns"]
    hash = hexdigest(input)
    adj_id = int(hash[::2], 16)
    noun_id = int(hash[1::2], 16)
    adjective = adjectives[adj_id % len(adjectives)]
    noun = nouns[noun_id % len(nouns)]
    return f"{OBF_PREFIX}{adjective}{sep}{noun}"


def obfuscate_str(name: typing.Optional[str], value: str):
    if re.match(r"^[0-9a-f]{12,}$", value, re.I):
        # must be a fake uuid
        if value.startswith(FAKE_UUID_PREFIX):
            # already obfuscated
            out = value
        else:
            expected_len = 32
            tail = hexdigest(value)[-(expected_len - len(FAKE_UUID_PREFIX)) :]
            out = f"{FAKE_UUID_PREFIX}{tail}"
            assert len(out) == expected_len
    elif re.match(r"^([0-9a-f]{2}-?){6}$", value, re.I):
        # MAC
        if value.startswith(FAKE_MAC_PREFIX):
            # already obfuscated
            out = value
        else:
            tail = hexdigest(value)
            out = f"{FAKE_MAC_PREFIX}-{tail[0:2]}-{tail[2:4]}-{tail[4:6]}-{tail[6:8]}".upper()
    elif "@" in value:
        out = generate_obfuscated_words(value, sep="@")
    elif name is None:
        out = value
    elif name.lower() in ("ssid", "name", "apname", "password", "wlanname"):
        out = generate_obfuscated_words(value)
    elif name.lower() in ("hostname"):
        out = generate_obfuscated_words(value, sep="-")
    else:
        out = value
    return out


def obfuscate(data: typing.Union[dict, list]):
    def _obfuscate_el(key, value):
        if isinstance(value, (dict, list)):
            new_value = obfuscate(value)
        elif isinstance(value, str):
            new_value = obfuscate_str(key, value)
        elif isinstance(value, (int, float, None)):
            new_value = value
        else:
            raise NotImplementedError(value)
        return new_value

    if isinstance(data, dict):
        out = {}
        for key, value in data.items():
            out[key] = _obfuscate_el(key, value)
    elif isinstance(data, list):
        out = [_obfuscate_el(None, el) for el in data]
    else:
        raise NotImplementedError(data)
    return out


def main(file_or_dir: str):
    root = pathlib.Path(file_or_dir)
    if not root.is_dir:
        files = [root]
    else:
        assert root.is_dir
        files = list(pathlib.Path(file_or_dir).glob("**/*.json"))

    for file in files:
        with file.open() as fin:
            input_data = json.load(fin)
        obfuscated_data = obfuscate(input_data)

        with file.open("w") as fout:
            json.dump(obfuscated_data, fout, indent=4, sort_keys=True)


if __name__ == "__main__":
    main(sys.argv[1])
