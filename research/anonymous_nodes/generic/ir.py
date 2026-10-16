"""Description IR — one object per unnamed mention (METHODOLOGY.md §3.2).

M1 fills mention/role/anchor text/relation phrases/constraints; M2 fills anchor.id; M3 fills
each phrase's KB paths from the relation lexicon; M4 compiles the paths for one KB.

A path is a list of hops; a hop is one or more alternative properties followed in one direction:
    Hop(props=["P22", "P25"], dir="out")   # father or mother of the current node
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import json

ANCHOR_REFS = ("topic", "mention", "description")
GENDERS = (None, "male", "female")


@dataclass
class Hop:
    props: list[str]
    dir: str = "out"                      # "out": anchor -> value; "in": value -> anchor

    def __post_init__(self):
        if isinstance(self.props, str):
            self.props = [self.props]
        assert self.props and self.dir in ("out", "in"), self


@dataclass
class Constraints:
    gender: Optional[str] = None
    ordinal: Optional[int] = None          # "eldest" = 1, "second" = 2 (WD qualifier P1545)
    time: Optional[str] = None             # "first", "last", or an ISO year
    type: Optional[str] = None             # expected class label, e.g. "Person"
    same_name_as_anchor: bool = False      # "his namesake nephew"
    plural: bool = False
    count: Optional[int] = None            # "his three sons"

    def __post_init__(self):
        assert self.gender in GENDERS, self.gender


@dataclass
class Anchor:
    ref: str                               # topic | mention | description
    text: str
    id: Optional[str] = None               # KB id once linked (M2)
    description: Optional["Description"] = None   # nested anchor ("the founder of Mérida")

    def __post_init__(self):
        assert self.ref in ANCHOR_REFS, self.ref
        if self.ref == "description":
            assert self.description is not None


@dataclass
class Description:
    mention: str
    role: str                              # subject | object of the extracted triple
    anchor: Anchor
    relation_phrases: list[str]            # outermost last: ["founder", "grandson"]
    constraints: Constraints = field(default_factory=Constraints)
    paths: dict = field(default_factory=dict)      # kb -> list of alternative paths (list[list[Hop]])
    evidence: dict = field(default_factory=dict)   # sentence_id, span

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def from_dict(d: dict) -> "Description":
        a = d["anchor"]
        nested = Description.from_dict(a["description"]) if a.get("description") else None
        paths = {kb: [[Hop(**h) for h in p] for p in alts] for kb, alts in d.get("paths", {}).items()}
        return Description(mention=d["mention"], role=d["role"],
                           anchor=Anchor(a["ref"], a["text"], a.get("id"), nested),
                           relation_phrases=list(d["relation_phrases"]),
                           constraints=Constraints(**d.get("constraints", {})),
                           paths=paths, evidence=d.get("evidence", {}))
