# readme-guardian npm package

This package is a thin Node.js launcher for the matching Python wheel bundled inside the npm tarball.

```bash
readme-guardian --status
readme-guardian --init
readme-guardian --apply
readme-guardian --check
```

The launcher needs `pipx`. It invokes `pipx run --spec <bundled-wheel>` using argument arrays, so it neither shells out through user-provided arguments nor installs a global Python package. The wheel is part of this npm tarball and is protected by npm's normal package-integrity verification.

The Python CLI does not make network calls or run project test/lint commands unless `--run-checks` is explicitly passed. See the source repository for the security model and release checksums:

https://github.com/jeevesh2515/readme-guardian
