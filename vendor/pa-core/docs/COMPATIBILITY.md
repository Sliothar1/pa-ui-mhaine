# Compatibility matrix and vendored-file checksums

Sites vendor a tagged release at `vendor/pa-core` (`git archive <tag>`), never `main`.

| Site (repo) | Pinned pa-core (code) | Since | Parity record |
|---|---|---|---|
| PA Uí Mhaine (Sliothar1/pa-ui-mhaine) | v0.2.0 | 11 Oct 2026 (was v0.1.0) | `docs/PARITY.md` in that repo: 36/36 published files byte-identical, draft and live |
| PA Réalt (Sliothar1/pa-realt) | v0.2.0 | 11 Oct 2026 | `prereg/addendum-2026-10-12.md` in that repo |

pa-core v0.3.0 (contract docs, edges, parity) is released; no site pins it yet.

Schema version: 1 in every release so far. Datasets may carry a `meta|schema_version` column on a
row (core column, unreleased on main after v0.2.0); validation fails if it differs from the
version the installed pa-core reads.

## sha256 of the vendored v0.2.0 tree (as committed in PA Uí Mhaine `vendor/pa-core`)
LICENSE (Apache-2.0) and NOTICE come from tag v0.2.1 (licence-only release); VENDORED.md is written by the site. All other
files are byte-identical to `git archive v0.2.0`. Check with
`cd vendor/pa-core && sha256sum -c` on the list below (paths relative to `vendor/pa-core`).

```
769ab350ef12e9d2f9939cc2dd3f92b6efc61c9930d90987a2116a65a902edff  .github/workflows/ci.yml
1919c7b88369e147fa2a3fd5c0c667746a1a7834939a95f8574c4c9fb32f1bac  .gitignore
2164a366c1c9b35d617a4e9fb741192fcb004fe2fd416ffe14765130c606fe54  CHANGELOG.md
cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30  LICENSE
eb3d7ba5ddb505f8d96f0effad0aa939acd076f3d6a2ab409c0cd73cf0f05d5d  NOTICE
c2e9272434c46e752514efa581355429783c18c063a6cb2d8e495afdd34c1b8e  README.md
531526bb8743d2a4a8accc4afe0ed3f6aa1adc579fb8407280f8d4440f9daa11  VENDORED.md
dff08dd23a858649226b0314dc4888b11e105a6c7f69c3f0955189fb7de2d81c  docs/SCHEMA.md
cf75a1401079f70b3a20f58c1b41f07dfff72943557fc83ac8e72b2e0e594e99  pa_core/__init__.py
b29b18dcdff7a1dc3835030d29e8eb69b6ccb6f0aa2ac7e9c72fd79d51e7a608  pa_core/adapters/__init__.py
227401e4db033e5008fa0f1b27ef45ff5418ddca993f3741e163fe912adadfa4  pa_core/adapters/json_claims.py
e9445aede36eccc29b3639dae3f928473d827a565e5e83bfebe38006b8c5162e  pa_core/adapters/tabular.py
fad6f2f144ccd4af88d9b194bfb1392415c79054c8a7c8d0428075fdd2c36c54  pa_core/cli.py
ae04ff510f0551e6846e4cfe33b17bcc68423719d4f3e1d02a3dc0935c77708c  pa_core/dataset.py
32d4a31d240f506e10dd8042d44c9ac4232255674ade4a036df48295fa258c4f  pa_core/diff.py
8042dd35f2c896b1aa030d77f90853b491f95eab4e4d4eb860d6dee939700460  pa_core/export.py
af5b7b4c9e9f7afa02de2c6bcf1073a7d75390e18e04440d9c0d8ef5228e38be  pa_core/inspect_row.py
9dbc99cdbf876e24a8b1f5b1c55470792b16140f6c02b44ce56378d1bb8a97a2  pa_core/provenance.py
884c1a0dbb11f5ebeeb64b0ee99bff7fdd06cfd955f2107006f85d40465687e8  pa_core/schema.py
54f1bc2eae92211d017adc32206b195042442fa6ffeb97e19b9d887b571732c4  pa_core/tsvio.py
a74bff82afe488ed4b8f5859bcfbdaff8bcd2710814e2d0140933d812c82f398  pa_core/validate.py
754dad6ba17964b680679f68e8484e60618b33bdc922a178d24682045e7d7e7b  pa_d4m.py
904b3a108c36808e978637dbfc42942c3a677a437c3caacd9056b08ec197fe3c  pyproject.toml
974ac72e303bdd685ce3c5d40eb40fd6580b40924ae333e22f391141f5f215a2  tests/fixtures/claims/adapter.json
a13a4b65f3066786d63329e798bc09d9dc88c07aff051aba8f035c290f8cba01  tests/fixtures/claims/allow.json
b518c21e5f1447642b712518bcbb5912810d2c2a2961d0a5a2138db45cb4978f  tests/fixtures/claims/claims.json
d238dab4d6a5aef81b64143c642045b3b4da4c206aba9ea290ec4dac08ca7a4f  tests/fixtures/claims/eras.json
db5eaf2a76d629f38f0cf71e47225c1960277b3df31b0f5e8cbf30bc2fd6edab  tests/fixtures/claims/schema.json
f5a57ab30bc111049e763e5e7393920adcc75de9366f9bf55e727685425161ef  tests/fixtures/sensitive/A_obs.tsv
a589b3dbf900b3d791435cf2db99234a78f329585e721ca504c2e9b121c41636  tests/fixtures/sensitive/A_prov.tsv
86be2fbcd10cd7ced8100874638e38f2599138ca21d0cf5411249ce5402a6a29  tests/fixtures/sensitive/allow.json
a0550e387f0dbce4eebef59abdc3c2d83120a661116ae22437c76a9f84cbee1d  tests/fixtures/sensitive/schema.json
d892f42c8eb7d5188b0672b222c8e741cccc550e4ff277b7cfda7213e05f7f39  tests/fixtures/table/adapter.json
6da28b307ca908f70247a2fb42f7f7b7273b3a029967d263fa3e33adf7fead8b  tests/fixtures/table/allow.json
ed375816d780c65fb0b7b687d0b5bd7dc22c6609799c86f48360bfea61808b4e  tests/fixtures/table/meta.json
a318e8b111b246c1a4d1fec5043c125ae974276a2876d48795de5e200712a1db  tests/fixtures/table/mon.csv
58c070017b923450dfd1b3b49f7f0499094279fade94d3cd269a3aed596021d7  tests/fixtures/table/schema.json
10513e7ba8fd1c7f1a78be9f8cdcd445f7d94c2d601d69fb51951247df80b16b  tests/test_core.py
```

v0.2.1 differs from v0.2.0 only in LICENSE, NOTICE, README, pyproject licence/version and `__version__`; sites pinned to v0.2.0 code carry the v0.2.1 LICENSE/NOTICE.
