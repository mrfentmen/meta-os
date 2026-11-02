# Service SDK (B-L1-119)

Two files and a template, generated from the pattern in `services/example/example.goose`
(B-L1-94) — which was itself written by copying the eighteen services that came before it.

| File | What it is |
|---|---|
| `TEMPLATE.goose` | A complete, compilable-in-shape service: init, one mutating function, one lookup, one health line, one failure helper. Copy it, rename `tpl_`, keep the structure. |
| `CHECKLIST.md` | The mechanical checks a new service must pass before anyone reviews it: matrix row, boot-order row, tests, status word. Every item traces to a file in this tree. |

## Why a template rather than a generator

A generator would be faster for the second service and worse for the twentieth: it hides the
decisions behind a flag. The template shows them. Every comment in `TEMPLATE.goose` is a
sentence someone had to write in a real service, and the copy keeps them in front of the
person writing the next one.

## Generating a service by hand, in order

1. `cp os-build/layer1/sdk/TEMPLATE.goose services/foo/foo.goose`
2. `sed -i '' 's/tpl_/foo_/g; s/TPL_/FOO_/g' services/foo/foo.goose`
3. Write the three paragraphs at the top — what it is, what it refuses, what it does not own.
   If the second one is empty, the design is not finished.
4. Append the id and row to `services/callmatrix/callmatrix.goose`; append the row to
   `services/supervisor/bootorder.goose`.
5. Add `services/foo/README.md` from `services/README_TEMPLATE.md`.
6. Add `services/tests/tNN_foo.goose`.
7. Run the two audits named in the checklist.

## The pattern in one paragraph

Fixed-size state in one struct, passed by reference; one function that mutates and returns
`(id, code)`; lookups that return a bool alongside the value; a health line that cannot fail;
failures counted and logged through one helper; sizes named as constants with a reason; a
`Status:` line that says WRITTEN until a build log exists. Everything else is the service's
own business, and this template deliberately has no opinion about it.
