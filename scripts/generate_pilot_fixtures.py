"""Deterministic, synthetic bilingual answers for the three-question pilot."""

import argparse
import copy
import json
import re
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDS = dict(re.findall(r'set\s+(\w+)\s*=\s*"([0-9a-f-]{36})"', (ROOT / "src/uuids.j2").read_text()))


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "science-europe-pilot/" + name))


def path(*names):
    return ".".join(IDS.get(name, name) for name in names)


def generate(language):
    values = {}

    def text(en, zh):
        return zh if language == "zh-Hant" else en

    def put(p, value, kind="StringReply"):
        values[p] = {"type": kind, "value": value}

    def choose(p, answer):
        put(p, IDS[answer], "AnswerReply")

    admin = path("adminDetailsCUuid")
    projects = path(admin, "projectsQUuid")
    project = path(projects, uid("project"))
    put(projects, [uid("project")], "ItemListReply")
    put(
        path(project, "projectNameQUuid"),
        text("Coastal observations: reproducible data management", "海岸觀測：可重現的資料管理"),
    )
    put(path(project, "projectNumberQUuid"), "COAST-2026")
    put(
        path(project, "projectAbstractQUuid"),
        text(
            "Synthetic example for evaluating template quality. The project re-uses open observations and documents data management decisions.",
            "本範例為模板品質測試而設計，使用合成的研究情境與回答。本計畫將再次使用開放觀測資料，並記錄資料管理決策。",
        ),
    )
    put(path(project, "projectStartQUuid"), "2026-01-01")
    put(path(project, "projectEndQUuid"), "2027-12-31")
    contributors = path(admin, "contributorsQUuid")
    contributor = path(contributors, uid("contributor"))
    put(contributors, [uid("contributor")], "ItemListReply")
    put(path(contributor, "contributorNameQUuid"), text("Example research team", "範例研究團隊"))
    put(path(contributor, "contributorEmailQUuid"), "research@example.org")
    put(
        path(contributor, "contributorRoleQUuid"),
        [
            IDS[n]
            for n in (
                "contributorRoleContactPersonAUuid",
                "contributorRoleCreatorOfDMPAUuid",
                "contributorRoleDataStewardAUuid",
            )
        ],
        "MultiChoiceReply",
    )
    measured = path("creatingCUuid", "measuredQUuid")
    choose(measured, "measuredNoAUuid")
    reuse = path("reusingCUuid", "preexistingQUuid")
    choose(reuse, "preexistingYesAUuid")
    datasets = path(reuse, "preexistingYesAUuid", "refDataQUuid")
    put(datasets, [uid("dataset-1"), uid("dataset-2")], "ItemListReply")
    for number in (1, 2):
        dataset = path(datasets, uid(f"dataset-{number}"))
        put(
            path(dataset, "refDataNameQUuid"),
            text(
                f"Open coastal observations — station {number}", f"開放海岸觀測資料——測站 {number}"
            ),
        )
        put(
            path(dataset, "refDataWhereQUuid"),
            f"https://example.org/datasets/coastal-observations/station-{number}/version-2026",
        )
        use = path(dataset, "refDataUseQUuid")
        choose(use, "refDataUseYesAUuid")
        used = path(use, "refDataUseYesAUuid")
        put(
            path(used, "refDataUsageQUuid"),
            text(
                "Compare seasonal changes in water temperature.\n\n- Retain the original timestamps.\n- Document any excluded observations.",
                "比較水溫的季節變化。\n\n- 保留原始時間戳記。\n- 記錄排除觀測值的原因。",
            ),
        )
        version = path(used, "refDataVersionedQUuid")
        choose(version, "refDataVersionedYesAUuid")
        put(path(version, "refDataVersionedYesAUuid", "refDataVersionedWhichQUuid"), "2026.1")
        choose(
            path(version, "refDataVersionedYesAUuid", "refDataVersionedChangeQUuid"),
            "refDataVersionedChangeStayAUuid",
        )
        choose(path(used, "refDataReproduceQUuid"), "refDataReproduceCopyAUuid")
        choose(path(used, "refDataConditionsQUuid"), "refDataConditionsCCBYAUuid")
        choose(path(used, "refDataFormatQUuid"), "refDataFormatUseAUuid")
    metadata = path("creatingCUuid", "metadataQUuid")
    choose(metadata, "metadataExploreAUuid")
    provenance = path(metadata, "metadataExploreAUuid", "provenanceQUuid")
    choose(provenance, "provenanceOtherAUuid")
    put(
        path(provenance, "provenanceOtherAUuid", "provenanceOtherQUuid"),
        text(
            "Record source versions and processing scripts in the project repository.\n\n| Record | Retention |\n|---|---|\n| Processing log | 10 years |\n| Source checksum | 10 years |",
            "在計畫的版本控制儲存庫記錄來源版本與處理程式。\n\n| 紀錄 | 保存期間 |\n|---|---|\n| 處理紀錄 | 10 年 |\n| 來源校驗碼 | 10 年 |",
        ),
    )
    shared = path("processingCUuid", "sharedWorkspaceQUuid")
    choose(shared, "sharedWorkspaceYesAUuid")
    how = path(shared, "sharedWorkspaceYesAUuid", "sharedHowQUuid")
    choose(how, "sharedHowExploreAUuid")
    choose(path(how, "sharedHowExploreAUuid", "sharedHowChangeQUuid"), "sharedHowChangeSameAUuid")
    reliable = path(shared, "sharedWorkspaceYesAUuid", "sharedReliableQUuid")
    choose(reliable, "sharedReliableExploreAUuid")
    choose(
        path(reliable, "sharedReliableExploreAUuid", "sharedReliablePreventLossQUuid"),
        "sharedReliablePreventLossStoredAUuid",
    )
    choose(
        path(reliable, "sharedReliableExploreAUuid", "sharedReliableBackupQUuid"),
        "sharedReliableBackupCopyBackupsAUuid",
    )
    expertise = path(admin, "additionalExpertiseQUuid")
    choose(expertise, "additionalExpertiseYesTrainAUuid")
    put(
        path(
            expertise,
            "additionalExpertiseYesTrainAUuid",
            "additionalExpertiseYesTrainTrainingQUuid",
        ),
        text(
            "Staff will complete training before data publication.\n\n- Metadata quality checks\n- Version control and provenance",
            "工作人員將於資料發布前完成培訓。\n\n- 後設資料品質檢核\n- 版本控制與資料溯源",
        ),
    )
    choose(path(admin, "additionalHWSWQUuid"), "additionalHWSWNoAUuid")
    costs = path(project, "costQUuid")
    put(costs, [uid("cost-1"), uid("cost-2")], "ItemListReply")
    for number, amount in ((1, "5000"), (2, "0")):
        cost = path(costs, uid(f"cost-{number}"))
        put(
            path(cost, "costTitleQUuid"),
            text(f"Data preparation resource {number}", f"資料整理資源 {number}"),
        )
        put(
            path(cost, "costDescriptionQUuid"),
            text("Prepare metadata and validate deposit files.", "整理後設資料並檢查寄存檔案。"),
        )
        put(path(cost, "costAmountQUuid"), amount)
        put(
            path(cost, "costCurrencyQUuid"),
            {"type": "PlainType", "value": "TWD"},
            "IntegrationReply",
        )
        put(
            path(cost, "costAllocationQUuid"),
            [IDS["costAllocationFindabilityAUuid"], IDS["costManagementAUuid"]],
            "MultiChoiceReply",
        )
        cover = path(cost, "costCoverQUuid")
        choose(cover, "costCoverOtherAUuid")
        put(
            path(cover, "costCoverOtherAUuid", "costCoverOtherHowQUuid"),
            text("Institutional research funds", "機構研究經費"),
        )
    partial = copy.deepcopy(values)
    cost1 = path(costs, uid("cost-1"))
    partial.pop(path(cost1, "costCurrencyQUuid"))  # Amount must remain visible.
    first = path(
        datasets, uid("dataset-1"), "refDataUseQUuid", "refDataUseYesAUuid", "refDataUsageQUuid"
    )
    partial.pop(first)  # Dataset 2 must remain intact.
    negative = {}
    for p, answer in (
        (measured, "measuredNoAUuid"),
        (reuse, "preexistingNoAUuid"),
        (shared, "sharedWorkspaceNoAUuid"),
        (path(shared, "sharedWorkspaceNoAUuid", "notSharedBackupQUuid"), "notSharedBackupNoAUuid"),
        (expertise, "additionalExpertiseNoAUuid"),
        (path(admin, "additionalHWSWQUuid"), "additionalHWSWNoAUuid"),
    ):
        negative[p] = {"type": "AnswerReply", "value": IDS[answer]}
    stress = copy.deepcopy(values)
    stress[first]["value"] += (
        "\n\n"
        + text(
            "Long descriptive text to exercise pagination. ",
            "此段較長的研究說明用於檢查跨頁排版、標點與中文字型。",
        )
        * 80
    )
    return {
        "empty": {},
        "negative": negative,
        "partial": partial,
        "populated": values,
        "stress": stress,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tooling", type=Path, required=True)
    args = parser.parse_args()
    for filename in ("root-2.7.0.km", "root-zh-hant-2.7.0.km"):
        bundle = ROOT / "fixtures/knowledge-models" / filename
        bundle.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.tooling.resolve() / "fixtures/knowledge-models" / filename, bundle)
    for language in ("en", "zh-Hant"):
        folder = ROOT / "fixtures/pilot" / language
        folder.mkdir(parents=True, exist_ok=True)
        for case, replies in generate(language).items():
            events = [
                {"type": "SetReplyEvent", "uuid": uid(f"{case}/{p}"), "path": p, "value": value}
                for p, value in sorted(
                    replies.items(), key=lambda item: (item[0].count("."), item[0])
                )
            ]
            (folder / f"{case}.events.json").write_text(
                json.dumps(events, ensure_ascii=False, indent=2) + "\n"
            )
            recipe = {
                "name": f"Science Europe pilot / {case}",
                "events_file": f"{case}.events.json",
                "knowledge_model_package_id": "../../knowledge-models/"
                + ("root-2.7.0.km" if language == "en" else "root-zh-hant-2.7.0.km"),
                "question_tag_uuids": [],
                "visibility": "PrivateProjectVisibility",
                "sharing": "RestrictedProjectSharing",
            }
            (folder / f"{case}.json").write_text(
                json.dumps(recipe, ensure_ascii=False, indent=2) + "\n"
            )
