# Log Intelligence Agent: web UI

Angular 22 single-page app for the Log Intelligence Agent API. See the
[project README](../README.md) for what the project does.

```bash
npm install
npm start                     # http://localhost:4200, proxies /api to http://127.0.0.1:8000
npx ng test --watch=false     # Vitest unit tests
npx ng build                  # production build in dist/log-intel-ui/browser
```

- `src/app/core/`: API client and app-wide state. The current investigation and the upload
  queue live here, so they keep running while you switch pages.
- `src/app/features/`: Overview (new investigation), History, Settings.
- `src/app/shared/`: upload drop zone, analysis result with cited log lines, icons.

In Docker, `nginx.conf` serves the build and proxies `/api` to the `api` service.
