# Frozen public Knowledge Model fixtures

These two unmodified public bundles are owned and versioned here as test inputs
for the custom English template. They contain KM definitions and their package
history, not private project contexts or questionnaire replies. Test preparation
only verifies the local files: it never downloads, upgrades or repairs them.

## Snapshot provenance

Both files are byte-identical to the snapshots formerly downloaded from
[`ThreeMonth03/dsw-document-template-tool` at
`25e339fbdfb1d20796471055790aad6a4226b6ed`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/25e339fbdfb1d20796471055790aad6a4226b6ed/fixtures/knowledge-models).
That repository is the historical snapshot source, not a build or network
dependency for these fixtures. No registry export or reserialization was used
when bringing the existing bytes into this repository.

| File | Bundle coordinate | Bytes | SHA256 |
| --- | --- | ---: | --- |
| `root-2.7.0.km` | `dsw:root:2.7.0` | 6,118,640 | `aabca6f7de8ad41cf9989afd25d4827f3de134fb8f0d965fcc6c336cfeb3e965` |
| `root-zh-hant-2.7.0.km` | `dsw:root-zh-hant:2.7.0` | 8,111,551 | `a3030cb9048a8842fe43ebac9ece00011e26936111789443d85422473c4cae47` |

The bundle metadata declares KM metamodel version `19`; this is not a document
template or document-context metamodel version, nor a new DSW runtime claim.
Replacing either snapshot requires a deliberate fixture change and review of its
checksum and template tests. A missing or corrupt file must be restored from the
English source checkout rather than silently replaced from a remote service.

## Attribution and licensing

The selected packages identify themselves as **Common DSW Knowledge Model** and
**Common DSW Knowledge Model (zh_Hant)**, version `2.7.0`, and declare
`Apache-2.0`. Their embedded README, contributor acknowledgements, changelog and
complete package metadata are retained unchanged. Each bundle also contains
historical packages: 42 declare `Apache-2.0`, while eight retain the historical
label `Apache-2`. These recorded labels have not been normalized or rewritten.

The repository's [Apache License 2.0](../../LICENSE) text accompanies these
fixtures. The historical Tool repository's own software licence is not a reason
to relabel the embedded KM packages; retain their original attribution and
licence metadata when redistributing them.
