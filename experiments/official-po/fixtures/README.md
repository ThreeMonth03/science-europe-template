# Historical catalog fixture

`zh-Hant-0.3.80.po` preserves the exact catalog used by the recorded local
0.3.80 and stock-4.35 smoke receipts (SHA-256
`900545fdaf41a89144914bec926251fe9f655bc69cbac0dbc7c610b3c5f9c42e`).
It is a read-only test/history fixture, not a translation source to maintain.

Edit only `locales/zh-Hant.po` in `ThreeMonth03/science-europe-template-zhtw`.
The English template retains Jinja, locale-aware layout and catalog validation;
build commands take the external PO explicitly.
