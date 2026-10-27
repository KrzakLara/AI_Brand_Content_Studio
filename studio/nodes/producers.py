"""Team 3 (production): carousel, hero and reel producers.

Each producer is a stage-cached step. Inside it, every provider call is an individual
ledger operation, so a crash mid-production resumes without repeating finished calls.
"""
import json
from collections.abc import Callable

from studio import prompts
from studio.contracts import ArtifactKind, CreativeSpec, PostFormat, PostStatus
from studio.fingerprint import fingerprint
from studio.services import Services

W, H = 1080, 1350  # 4:5 feed format

PRODUCER_NAME = {
    PostFormat.CAROUSEL.value: "carousel_producer",
    PostFormat.HERO.value: "hero_producer",
    PostFormat.REEL.value: "reel_producer",
}


def _spec_op(svc: Services, s: dict, stage: str, fp: str, producer: str) -> CreativeSpec:
    claims = {e["evidence_id"]: e["claim"] for e in s["evidence"]["items"]}
    raw = svc.op(
        node=producer, scope=s["post_id"], stage=stage, fp=fp, suffix="spec", provider=svc.llm.info,
        fn=lambda: svc.llm.structured(CreativeSpec, task="creative_spec", payload={
            "post_plan": s["plan_post"], "palette": s["brand"]["palette"],
            "evidence_claims": claims, "attempt": s.get("attempt", 0),
            "repair_instructions": s.get("repair_instructions", []),
        }).model_dump())
    return CreativeSpec.model_validate(raw)


def _image_op(svc: Services, s: dict, stage: str, fp: str, producer: str, name: str,
              prompt: str, seed: int, extra: dict) -> dict:
    post_id = s["post_id"]

    def fn() -> dict:
        data = svc.image.generate(prompt=prompt, width=W, height=H, seed=seed,
                                  meta={"post_id": post_id, "name": name})
        ref = svc.write_artifact(post_id, fp, name, data, ArtifactKind.IMAGE, "image/png",
                                 svc.image.info.is_mock, {"width": W, "height": H, **extra})
        return ref.dump()

    return svc.op(node=producer, scope=post_id, stage=stage, fp=fp, suffix=name,
                  provider=svc.image.info, fn=fn, artifact_of=lambda r: r, verify=svc.artifact_ok)


def _spec_doc(svc: Services, post_id: str, fp: str, spec: CreativeSpec) -> dict:
    data = json.dumps(spec.dump(), indent=2, sort_keys=True).encode("utf-8")
    return svc.write_artifact(post_id, fp, "creative_spec.json", data, ArtifactKind.DOCUMENT,
                              "application/json", spec.mock).dump()


def _build_carousel(svc, s, stage, fp, producer):
    spec = _spec_op(svc, s, stage, fp, producer)
    arts = [_image_op(svc, s, stage, fp, producer, f"slide_{i + 1}.png",
                      f"{spec.visual_prompt} | {sl.title}", i, {"slide": i + 1})
            for i, sl in enumerate(spec.slides)]
    return spec, arts + [_spec_doc(svc, s["post_id"], fp, spec)]


def _build_hero(svc, s, stage, fp, producer):
    spec = _spec_op(svc, s, stage, fp, producer)
    art = _image_op(svc, s, stage, fp, producer, "hero.png", spec.visual_prompt, 0, {})
    return spec, [art, _spec_doc(svc, s["post_id"], fp, spec)]


def _build_reel(svc, s, stage, fp, producer):
    spec = _spec_op(svc, s, stage, fp, producer)
    cover = _image_op(svc, s, stage, fp, producer, "cover.png", spec.visual_prompt, 0, {"role": "cover"})
    post_id = s["post_id"]
    storyboard = {"headline": spec.headline, "body": spec.body, "cta": spec.cta,
                  "shots": [{"n": i + 1, "prompt": f"{spec.visual_prompt} | shot {i + 1}"}
                            for i in range(3)]}

    def fn() -> dict:
        data = svc.video.generate(storyboard=storyboard, duration_s=spec.duration_s,
                                  meta={"post_id": post_id})
        return svc.write_artifact(
            post_id, fp, "reel.mock.json" if svc.video.info.is_mock else "reel.mp4", data,
            ArtifactKind.VIDEO_PLACEHOLDER if svc.video.info.is_mock else ArtifactKind.VIDEO,
            "application/json" if svc.video.info.is_mock else "video/mp4",
            svc.video.info.is_mock, {"duration_s": spec.duration_s}).dump()

    video = svc.op(node=producer, scope=post_id, stage=stage, fp=fp, suffix="video",
                   provider=svc.video.info, fn=fn, units=spec.duration_s,
                   artifact_of=lambda r: r, verify=svc.artifact_ok)
    return spec, [cover, video, _spec_doc(svc, post_id, fp, spec)]


_BUILD = {PostFormat.CAROUSEL.value: _build_carousel, PostFormat.HERO.value: _build_hero,
          PostFormat.REEL.value: _build_reel}


def _production_fp(svc: Services, s: dict) -> str:
    fmt = s["plan_post"]["format"]
    wanted = set(s["plan_post"]["evidence_ids"])
    evidence = [e for e in s["evidence"]["items"] if e["evidence_id"] in wanted]
    providers = [svc.llm.info, svc.image.info] + ([svc.video.info] if fmt == "reel" else [])
    return fingerprint(
        "produce", s["plan_post"], s["brand"], evidence, [p.fingerprint() for p in providers],
        prompts.version("creative_spec"), s.get("attempt", 0), s.get("repair_instructions", []))


def make_producer(svc: Services, fmt: str) -> Callable[[dict], dict]:
    producer = PRODUCER_NAME[fmt]

    def node(s: dict) -> dict:
        attempt = s.get("attempt", 0)
        stage = f"produce#{attempt}"
        fp = _production_fp(svc, s)

        def compute() -> dict:
            spec, arts = _BUILD[fmt](svc, s, stage, fp, producer)
            return {"creative_spec": spec.dump(), "artifacts": arts}

        out, _ = svc.stage(s["post_id"], stage, fp, compute)
        return {
            "creative_spec": out["creative_spec"], "artifacts": out["artifacts"],
            "production_fp": fp, "production_history": [*s.get("production_history", []), fp],
            "status": PostStatus.VALIDATING.value,
        }

    node.__name__ = producer
    return node
