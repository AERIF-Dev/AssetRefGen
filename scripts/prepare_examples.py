"""Build public example inventories from original artwork; never calls an image service."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
VIEWS = ["front", "left", "back", "right"]
STYLE = "hand-painted storybook game concept, soft matte surfaces"


def subject(identifier, name, category, source, box, identity, inferences, group):
    return {"id": identifier, "name": name, "category": category, "style": STYLE,
            "master": "master_front.png", "views": VIEWS, "origin": "source-derived",
            "regions": [{"source_id": source, "box": box}], "identity_spec": identity,
            "inferences": inferences,
            "group": {"id": group, "label": group.capitalize()},
            "separation_rationale": "Distinct silhouette and distinguishing construction in the source."}


def inventories():
    characters = [
        subject("kiln-traveler", "Kiln traveler", "humanoid", "characters", [0, 160, 575, 940],
                {"silhouette": "squat terracotta domed kiln biped, open chimney",
                 "features": "cream arched face, two round eyes, one pale blue chest medallion",
                 "anatomy": "two segmented arms with mitten fists, two short legs and broad feet",
                 "pose": "neutral standing, arms slightly separated",
                 "front": "face and badge", "sides": "left faces image-left, right faces image-right"},
                ["Rear is a provisional continuous brick dome/barrel without another face or badge."], "cast"),
        subject("pond-courier", "Pond courier", "creature", "characters", [600, 110, 980, 940],
                {"silhouette": "lanky green frog biped with broad smooth oval head",
                 "features": "ochre poncho, two eyes, long arms and legs, webbed hands and three-toed feet",
                 "anatomy": "two arms and two legs, no visible tail", "pose": "natural relaxed standing"},
                ["Poncho rear and hidden joints are provisional; retain simple garment construction."], "wildlife"),
        subject("moth-keeper", "Moth keeper", "creature", "characters", [1030, 230, 1536, 940],
                {"silhouette": "round pear-shaped indigo moth, two feathered antennae",
                 "features": "orange oval eyes, lavender scarf, two small arms, two short feet, hanging wings",
                 "anatomy": "two arms, two feet, two wing covers, two antennae", "pose": "resting, wings closed"},
                ["Hidden rear wing attachment is provisional; no additional limbs inferred."], "wildlife"),
    ]
    objects = [
        subject("survey-rover", "Survey rover", "vehicle", "objects", [10, 140, 820, 920],
                {"silhouette": "rounded teal vehicle with four chunky wheels on two axles",
                 "features": "cream front bumper, centered amber lamp, short mast with red ball sensor",
                 "state": "assembled, wheels straight, mast fixed", "front": "lamp and cream bumper"},
                ["Far fourth wheel and hidden rear/underbody are provisional, preserve four-wheel design."], "equipment"),
        subject("signal-lantern", "Signal lantern", "prop_machinery", "objects", [1080, 20, 1645, 915],
                {"silhouette": "copper six-sided lantern with arched handle and broad dark base",
                 "features": "amber glass chamber, domed cap, one bail handle",
                 "state": "assembled upright, handle upright", "front": "one broad pane centered toward viewer"},
                ["Hidden frame edges complete a regular six-sided chamber; exact rear seam layout unknown."], "equipment"),
    ]

    def inventory(mode, sources, assets, rationale, order="per-asset-complete"):
        return {"schema_version": 1, "mode": mode, "quality": "quick", "generation_order": order,
                "count_rationale": rationale, "sources": sources, "assets": assets}

    char_source = {"id": "characters", "path": "sources/characters.png"}
    obj_source = {"id": "objects", "path": "sources/objects.png"}
    output = {
        "characters.inventory.json": inventory("roster", [char_source], characters,
            "Three distinct silhouettes and constructions; these are not alternate views.", "all-masters-first"),
        "objects.inventory.json": inventory("roster", [obj_source], objects,
            "A wheeled rover and a lantern have distinct functions, silhouettes and components."),
        "single.inventory.json": inventory("single", [char_source], [characters[0]],
            "One requested kiln traveler, located in the left portion of the source."),
        "folder.inventory.json": inventory("folder", [char_source, obj_source], characters + objects,
            "Two original concept images, five unique subjects total; no shared design across these two files."),
    }
    sheet = EXAMPLES / "kiln-traveler/contact_sheet.png"
    if sheet.exists():
        one = dict(characters[0], regions=[{"source_id": "turnaround", "box": box} for box in
            ([21,147,1275,1401], [1296,147,2550,1401], [2571,147,3825,1401], [3846,147,5100,1401])],
            separation_rationale="The same chimney, brick dome/body and limbs recur at four camera angles; one identity.")
        output["multiview.inventory.json"] = inventory("single",
            [{"id": "turnaround", "path": "kiln-traveler/contact_sheet.png"}], [one],
            "Four directional panels of the same kiln traveler; count one, not four.")
        repeated = dict(characters[0], regions=characters[0]["regions"] + one["regions"],
            separation_rationale="The kiln in the lineup and its four-angle sheet share the same distinctive identity.")
        output["repeated-folder.inventory.json"] = inventory("folder",
            [char_source, {"id": "turnaround", "path": "kiln-traveler/contact_sheet.png"}],
            [repeated, *characters[1:]],
            "Seven appearances across two images resolve to three distinct designs, including one four-angle sheet.")
    return output


if __name__ == "__main__":
    for filename, data in inventories().items():
        path = EXAMPLES / filename
        encoded = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") != encoded:
            raise SystemExit(f"Existing inventory differs: {path}; review before replacing.")
        if not path.exists():
            path.write_text(encoded, encoding="utf-8")
        print(filename, len(data["assets"]))
