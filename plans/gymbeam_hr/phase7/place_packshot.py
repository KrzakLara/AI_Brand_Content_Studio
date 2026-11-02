"""Place the official creatine packshot so that the two tests that are skipped in a bootstrapped workspace can run (Phase 7E).

The two skipped tests (tests/test_provenance.py::test_the_contact_sheet_is_built_from_the_hash_checked_original_and_refuses_another_image and
tests/test_strategy.py::test_a_tampered_packshot_file_is_detected) need ONE external file that is not redistributed: GymBeam's official packshot
  https://gymbeam.hr/media/catalog/product/cache/70f742f66feec18cb83790f14444a3d1/c/r/creatine-monohydrate-unflavoured-01_8.jpg
  SHA-256 99543edff63b17e355cd7bfcc734ef364ae81f08304e561e6a347c09e8954f1c
The second test also needs the cut-out derived from it; that is NOT downloaded: it is regenerated here with the project's own deterministic function
(studio.tools.imagecheck.cutout_background, tolerance 14) and checked against the recorded hash 86613b3f58580bf96b4e3517095682da0842a4ba389b3e97db89eb50ce7023d8.

  python tools/place_packshot.py --workspace C:/work/ws --file C:/Users/me/Downloads/creatine-monohydrate-unflavoured-01_8.jpg
Run it with the workspace's virtual environment (it imports studio.tools.imagecheck). Nothing is downloaded; a file with a different hash is refused."""
import argparse
import hashlib
import sys
from pathlib import Path

ORIG_SHA = "99543edff63b17e355cd7bfcc734ef364ae81f08304e561e6a347c09e8954f1c"
CUT_SHA = "86613b3f58580bf96b4e3517095682da0842a4ba389b3e97db89eb50ce7023d8"
RUN = Path("runs/research-gymbeam-hr-live/research")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, required=True, help="the bootstrapped workspace")
    ap.add_argument("--file", type=Path, required=True, help="the officially downloaded packshot image")
    a = ap.parse_args()
    ws = a.workspace.resolve()
    data = a.file.read_bytes()
    got = hashlib.sha256(data).hexdigest()
    if got != ORIG_SHA:
        sys.exit(f"REFUSED: SHA-256 {got} is not the recorded {ORIG_SHA}. The shop image may have changed; the tests need the exact recorded file.")
    sys.path.insert(0, str(ws))
    from studio.tools.imagecheck import cutout_background
    cut, _ = cutout_background(data)
    if hashlib.sha256(cut).hexdigest() != CUT_SHA:
        sys.exit("derived cut-out does not match the recorded hash; not writing it")
    (ws / RUN / "raw").mkdir(parents=True, exist_ok=True); (ws / RUN / "packshots").mkdir(parents=True, exist_ok=True)
    (ws / RUN / "raw/99543edff63b17e3.jpg").write_bytes(data)
    (ws / RUN / "packshots/86613b3f58580bf9_cutout.png").write_bytes(cut)
    print("placed original + regenerated cut-out (both hashes verified). Now run pytest in the workspace: expect 249 passed, 0 skipped.")


if __name__ == "__main__":
    main()
