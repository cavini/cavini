# tools

`gen-banner.py` writes `assets/terminal-{dark,light}.svg`, the animated terminal
at the top of the profile. Edit `LINES` and regenerate:

```bash
python3 tools/gen-banner.py              # the animated pair
python3 tools/gen-banner.py ./out --static   # frozen, for checking the layout
```

No dependencies — it is string formatting over the standard library.

Two things in there are deliberate and easy to break:

- Every clip rect carries its **finished** width as the static attribute, and a
  single animation spanning the whole timeline overrides it. A renderer that
  ignores SMIL therefore shows the completed terminal rather than an empty
  window.
- Glyph advances are pinned with `textLength`, so the typing cursor lands on
  the character it is typing whatever monospace font the reader happens to
  have installed.
