# Contributing

Thanks for wanting to make reel-studio better.

- **Made a reel with it?** Open an issue titled "Made with reel-studio" with the link. We love seeing them.
- **Found a bug?** Open an issue with the command you ran, the last lines of the failing log
  (`renders/build.log`, `renders/render_w0.log` or the pipeline output) and your OS + Blender version.
- **New presets** (faces, poses, shots, monitor templates, music styles): open a pull request with one
  example episode that uses them and its `renders/stills/sheet.jpg` attached to the PR description.
- **Docs and the playbook:** every fact needs a source, same rule as the episodes.

Please keep pull requests small and focused, and don't commit renders, audio takes or `.blend` files:
`.gitignore` already skips them inside `examples/` and `episodes/`.
