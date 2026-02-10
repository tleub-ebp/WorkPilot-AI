# Root `pnpm run dev` Usage

You can now start both the backend and frontend in development mode from the root of the repository with:

```sh
pnpm install # at the root, to install all dependencies including 'concurrently'
pnpm run dev
```

This will launch:
- The backend (Python, via `python run.py` in `apps/backend`)
- The frontend (Electron/Vite, via `pnpm run dev` in `apps/frontend`)

Both will run in parallel. If you need to change the backend or frontend dev commands, edit their respective `package.json` files.
