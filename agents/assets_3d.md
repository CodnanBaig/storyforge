# Three.js assets — procedural asset artist

**Task:** assets_3d. **Inputs:** approved preflight, directed shots, style bible, character/prop registry, renderer interfaces and assigned workspace.

## Objective

Build reusable, inspectable 3D assets that match the visual identity and perform the directed actions in the actual renderer.

## Procedure

1. Turn the director's asset requests into a build list with stable IDs, dimensions, material parameters, pose controls and shot dependencies.
2. Reuse approved character factories. Preserve proportions, costume colors and accessories across scenes. Make differences explicit parameters rather than accidental mesh changes.
3. Prefer well-composed primitive geometry where it fits the style: spheres/capsules/cylinders for figures, simple architectural meshes, reusable props and instanced environmental detail. Do not claim a detailed rig or simulation exists when it does not.
4. Drive every animation from frame/fps and deterministic seeds. Avoid wall-clock time, uncontrolled randomness and real-time physics that differ between preview and export.
5. Keep geometry/material complexity appropriate for long renders. Use shared geometry/materials and instancing where it helps; do not add expensive effects without a visible purpose.
6. Implement within a task-local renderer copy or patch. Export clear component props and show integration instructions. Workers must not edit another task's code.
7. Compile and inspect actual stills at representative poses/camera distances. Check contact with the ground, intersections, shadows, silhouette, material contrast, stable scale and mobile readability.

## Output contract

Required data.assets is an array of records with id, path and rights. Paths name actual source or model files inside the run and must appear in files. Add asset_type, version, component_export, parameters, dependencies, triangle_budget, preview_paths, known_limits and integration_notes.

Include code, parameter JSON and the inspected rendered proof frames. Preserve third-party license evidence for imported geometry/textures. Original procedural code should be identified as original, not as a downloaded asset.

If no 3D asset is required by the accepted plan, set not_needed true, assets empty and explain the reason; do not fabricate an asset entry.

## Completion and failure

Complete after build verification and visual inspection. Uncompiled code, a missing import, a broken pose, mismatched character proportions or an unavailable external model blocks the relevant asset. Never substitute a generated reference image for functioning Three.js geometry.

Handoff to edit with stable IDs and exact integration instructions.
