from pathlib import Path

path = Path("tests/deep_history/test_release_publisher.py")
text = path.read_text(encoding="utf-8")
old = '''        source.freeze(); next((self.root/"tamper").glob("*.json")).write_text('{"value":2}')
'''
new = '''        source.freeze()
        frozen_response=next(
            candidate
            for candidate in (self.root/"tamper").glob("*.json")
            if candidate.name != "manifest.json"
        )
        frozen_response.write_text('{"value":2}')
'''
if text.count(old) != 1:
    raise RuntimeError(f"expected one frozen-source tamper target, got {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("RELEASE_PUBLISHER_TAMPER_TEST_FIX=MATERIALIZED")
