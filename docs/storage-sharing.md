# 0.3.0: storage facts and publication reading blocks

Work branch: `feat/storage-sharing-readability`, based on 0.2.2. Official baseline
remains upstream 1.30.1 at `22d60aae4b63ee677477ac0c73097807284aaf9f`.
This is not a release, live deployment, new KM, or second Chinese Jinja implementation.

## Q5: mapped facts are narrower than the Science Europe topic

The compiled Common KM 2.7.0 asks about shared-workspace specialist management,
cold archival during the project, archival medium, remote storage, changes to
archived data, the need for frequent backups, and reliance on backups for human
error recovery. Q5 now independently retains these answers where supplied.

Neither a tape/disk choice nor a remote-location Yes names a storage site.
The frequent-backup Yes/No describes need, not an implemented daily/weekly cadence.
Recovery waiting time is not backup frequency. Access-restricted publication
repository choices are not working storage. Those concepts must not be conflated.
Exact sites and schedules remain explicitly outside what these mapped answers
establish. No inference is made about other free-text answers elsewhere in a project.
KM extensions for named services/sites and schedules require a separate decision.

`archivedDuringReNoAUuid` previously pointed to a real UUID belonging to the next
question. Correcting it demonstrates why a zero absent-UUID count is insufficient.
`audit_storage_mapping.py` checks option membership and records compiled paths
and labels in both EN/ZH KMs. `validate_pilot_fixtures.py` checks reachable inputs.

## Q10–Q13: presentation and partial answers

Dataset identity remains explicit in every relevant question, but no longer adds
an outer bullet-list level. Publication distributions and licence entries are
flat blocks. Free-answer lists/tables are not flattened or rewritten. Q10 retains
licence/date independently of repository and access choice and emits specific gaps.
Q13 retains the affirmative PID decision even if assigner details are absent.

Redundant lead-in sentences are removed, not supplied facts. PDF styles support
the owned blocks. Word body paragraph spacing is 4 pt instead of 6 pt; font size
and line spacing are unchanged. Only fixed PID policy paragraphs are joined via
the existing owned `dataset-policy` rule.

Old synthetic fixtures are unchanged. `storage-sharing` adds verified archival
answers plus a second, preliminary restricted distribution. Its partial variant
removes independent siblings while retaining dates, licence terms, links and PID
details. Neither is a complete scientific or financial plan.

## Upgrade obligations

Review upstream changes to Q5/Q10–Q13 against owned rendering and branch tests.
Do not overwrite these files or Word style preparation wholesale. Keep the
upstream baseline unchanged for selective ports. The Chinese repository locks
the reviewed English commit, refreshes translations and audits complete output.
Worker table support remains a separate pinned experimental dependency.
