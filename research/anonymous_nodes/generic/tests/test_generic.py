"""Offline tests always run; live Wikidata tests run with NEF_LIVE=1 (cached after the first run).
Run from research/anonymous_nodes:  python -m pytest generic/tests -q"""
import os, json, pytest
from generic.ir import Description, Anchor, Constraints, Hop
from generic.lexicon import expand, entry, lexicon

LIVE = os.environ.get("NEF_LIVE") == "1"


def test_lexicon_shapes():
    for noun, e in lexicon().items():
        if noun.startswith("_"): continue
        for kb in ("wikidata", "dbpedia"):
            for path in e.get(kb, []):
                assert path and all(isinstance(h, list) and h for h in path), (noun, kb)
        assert e.get("gender") in (None, "male", "female"), noun


def test_expand_nested_and_synonyms():
    alts, g = expand(["founder", "grandson"], "wikidata")
    assert g == "male" and [[h.props for h in p] for p in alts] == [[["P112"], ["P40"], ["P40"]]]
    alts, g = expand(["brother-in-law"], "wikidata")
    assert len(alts) == 2 and g == "male"
    assert entry("Daughters")["gender"] == "female"
    assert expand(["stepfather"], "dbpedia") == (None, None)      # not modelled in DBpedia


def test_ir_roundtrip():
    inner = Description("the founder of Mérida", "anchor", Anchor("mention", "Mérida", "Q165204"), ["founder"])
    d = Description("the grandson of the founder of Mérida", "object",
                    Anchor("description", "the founder of Mérida", description=inner), ["grandson"],
                    Constraints(gender="male"), paths={"wikidata": [[Hop(["P40"]), Hop(["P40"])]]})
    back = Description.from_dict(json.loads(d.to_json()))
    assert back.anchor.description.anchor.id == "Q165204" and back.paths["wikidata"][0][1].props == ["P40"]


@pytest.mark.skipif(not LIVE, reason="set NEF_LIVE=1")
def test_wikidata_known_cases():
    from generic.kb_wikidata import WikidataKB
    kb = WikidataKB()
    # Marie Antoinette's husband: two truthy P26 values -> ambiguous (16 Oct smoke test)
    r = kb.values("Q47365", expand(["husband"], "wikidata")[0], "male")
    assert len(r["known"]) >= 2
    # Uesugi Harunori's father: one answer, label only in Japanese
    q = kb.qid_for_title("Uesugi Harunori")
    r = kb.values(q, expand(["father"], "wikidata")[0], "male")
    assert r["known"] == ["Q11595125"] and kb.labels(r["known"])["Q11595125"] == "秋月種美"
    # father is schema-unique (single-best-value), spouse is not
    assert kb.schema_unique(expand(["father"], "wikidata")[0])
    assert not kb.schema_unique(expand(["husband"], "wikidata")[0])


@pytest.mark.skipif(not LIVE, reason="set NEF_LIVE=1 (needs the local nef-oxigraph store)")
def test_dbpedia_known_cases():
    from generic.kb_dbpedia import DBpediaKB
    kb = DBpediaKB()
    alts, g = expand(["husband"], "dbpedia")
    r = kb.values("Marie_Antoinette", alts, g)
    # one spouse in DBpedia, two in Wikidata: the same description is unique on one KB, ambiguous on the other
    assert r["known"] == ["Louis_XVI_of_France"] and r["gender_checked"] is False
    assert not kb.schema_unique(expand(["father"], "dbpedia")[0])     # no functional object properties
    assert kb.labels(["Louis_XVI_of_France"])["Louis_XVI_of_France"] == "Louis XVI of France"
    assert "France" in kb.ancestors("Paris")


@pytest.mark.skipif(not LIVE, reason="set NEF_LIVE=1")
def test_disambiguation_pages_are_not_linked():
    from generic.kb_wikidata import WikidataKB
    kb = WikidataKB()
    assert kb.qid_for_title("American") is None                                  # a disambiguation page
    assert kb.qid_for_title("American", reject_disambiguation=False) == "Q463180"
    assert kb.qid_for_title("Marie Antoinette") == "Q47365"
