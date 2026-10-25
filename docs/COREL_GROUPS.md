# PDF colour groups — 0.10.2 preview

The imported PDF must produce one image group, with one immediate subgroup per RGB, containing editable curves. A compound curve per colour does not satisfy this contract.

Each colour is now a PDF Form XObject with an explicit isolated DeviceRGB transparency group. CorelDRAW 26 (2025) retains these as groups, including singleton groups. Page content calls the colour Forms directly: an extra enclosing Form would introduce an unwanted third group level. Corel supplies the outer imported-file group.

Disconnected outer contours become separate painted curves within their colour Form. Holes stay with their enclosing outer contour; source coordinate strings and Bezier control points are retained. Ambiguous touching contours remain compound rather than risking a changed fill. No raster images, invisible placeholder shapes, or duplicate paths are added.

## Verification, 2026-10-25

- Native CorelDRAW import, as curves: synthetic two-colour PDF produced one file group, two colour subgroups, with one blue curve and two red curves.
- Native import of the user photo traced with nine colours: one file group, nine immediate colour subgroups. Expanded green subgroup contains 140 individual curves. Local screenshot and saved CDR retained outside the repository.
- Unlimited-colour photo export: 530 colour Forms. Poppler at 144 dpi matches previous PDF exactly in RGB pixels.
- Nine-colour export: Poppler at 72 dpi differs by mean 0.000011 channel levels, maximum 3/255, due to changed compositing/antialiasing. Vector coordinates are unchanged.
- `tests/pdf_color_groups.py`: separate curves, singleton grouping, both contour windings, holes, inherited fill, equivalent RGB case, vector-only PDF, and geometry XOR.
- Existing colour, photo-region and progress/export layout checks pass.

Re-export PDFs using 0.10.2 or later. Already saved PDFs retain their old structure. Other importers can interpret PDF grouping differently; this hierarchy was checked in CorelDRAW 26.
