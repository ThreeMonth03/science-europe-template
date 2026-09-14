# Repository contact answer ownership (0.3.11 experiment)

The Other-contact free answer belongs in Q11, alongside its repository destination.
Q10 retains the repository identity and all access/licence facts, but references
Q11 instead of copying the same free answer. Other fixed contact choices remain
unchanged in this bounded pass. No global text deduplication is performed.

The source question does not establish that Other means avoiding direct contact.
Q11 therefore uses the neutral lead “Other repository contact arrangements:”. A
blank answer has an explicit missing marker, not a claim that arrangements exist.

References target the dataset and distribution positions in the same rendered
document (`repository-contact-N-M`). They do not rely on unique dataset names,
hard-coded page numbers, or a non-missing-row counter. Inactive publication and
repository choices must not produce references or reveal stale child answers.
These are document-local anchors, not persistent IDs across edited questionnaires.

No CSS, Lua, reference DOCX, KM bindings, official question titles or upstream
baseline change. This remains the derivative of official 1.30.1. Upgrade checks
must cover BOTH Q10 and Q11; a clean Git merge cannot establish that a reference
still points to the correct answer in HTML, PDF and Word.

Synthetic verification includes the unchanged 60-paragraph `repository-long`
fixture and a new `contact-mixed` fixture: paragraph/list/table/link preservation,
an unanswered Other field, duplicate dataset names and identical text supplied
in two different fields. Each field retains its own full answer once; the two
independently supplied identical answers must both remain. Table fidelity still
depends on the previously isolated worker experiment. This is not full Science
Europe coverage, production deployment or target Microsoft Word acceptance.
