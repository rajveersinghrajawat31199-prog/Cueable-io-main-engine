# Real icons

No placeholder shapes for product icons, ever. Every icon in a scene is the product's own.

## Mac apps

Icons live in `/System/Applications/<App>.app/Contents/Resources/*.icns`. Convert:

```bash
sips -s format png "/System/Applications/Notes.app/Contents/Resources/<file>.icns" --out assets/icons/notes.png
```

Some apps keep the icon elsewhere (`/Applications/`, `Contents/Resources/AppIcon.icns`); look
inside that one bundle, do not scan the disk. Apple-app extraction is for spec and portfolio
work only.

## Web products

Use the SVGs and logos that `npx hyperframes capture` downloaded (`.capture/assets`), or inline
the site's own SVG markup. Never redraw an icon from memory.

## Storage

Put every extracted icon in the project's `assets/icons/` and give it a ref id in the
AssetManifest so scenes and the critique can cite it. Only use icons the user has rights to.
