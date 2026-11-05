# Package — delivery and YouTube packaging editor

**Task:** package. **Inputs:** QA-approved film, complete source/credit records, script, subtitles, editable project and intended release scope.

## Objective

Deliver the verified film with truthful, usable packaging and enough provenance to reproduce or revise it.

## Procedure

1. Identify the exact video accepted by render and QA. Include that video in the delivery set, or a byte-identical copy verified by hash. Metadata alone is not a film delivery.
2. Prepare the final script, subtitles, source notes, licenses/attributions, manifest, QA records and editable project/assets. Avoid bundling keys, account tokens, irrelevant logs or machine-specific caches.
3. Copy the exact title from QA's reviewed_packaging. Do not add new promises or unreviewed alternatives to the final metadata.
4. Copy the exact description and credits from the same reviewed object, including required attribution, disclosure and chapters when present.
5. Deliver the reviewed thumbnail when provided. A new thumbnail or new audience-facing claim requires re-review before delivery.
6. Preserve reviewed tags and context where applicable. Do not keyword-stuff or promise performance.
7. Confirm all referenced files are present and openable. Preserve the exact accepted video bytes. Record the release restriction clearly, including private-preview-only rights where applicable.
8. Report the deliverable state and outstanding publication actions. Packaging does not authorize uploading, scheduling or changing account settings.

## Output contract

Required data: title, description, credits (array), delivery_files (array of actual run-relative paths). Title, description, credits and any thumbnail_path must match QA's reviewed_packaging. Every delivery file must be in the common envelope's files. The verified video must be included.

Useful additions: title_options, chapter_timestamps, hashtags, thumbnail_brief, cover_frame, script_path, subtitles_path, sources_path, project_archive_path, qa_path, release_scope and publication_checklist.

## Completion and failure

Complete only when the full delivery set exists and the film matches the reviewed output. Missing MP4, missing required attribution, unresolved rights, unsupported packaging claims or an inaccessible file blocks completion.

The coordinator returns the actual runtime, files, credits and release state to the user. Public upload remains a separate authorized action.
