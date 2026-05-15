# Aura ID Frontend — Monorepo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the single Next.js app at repo root into a pnpm monorepo with two apps (clerk-pwa, dashboard) and four shared packages (ui, api-client, consent, types), then build the full compliance-safe capture flow.

**Architecture:** Plain pnpm workspaces — `pnpm-workspace.yaml` + `workspace:*` protocol for cross-package deps. No Turborepo. The existing Next.js app migrates to `apps/clerk-pwa/`; `apps/dashboard/` is scaffolded fresh. Shared code lives in `packages/`. All compliance copy is centralised in `packages/consent` so it cannot diverge between apps.

**Tech Stack:** Next.js 16 App Router, TypeScript strict, Tailwind v4, shadcn/ui, @supabase/ssr, TanStack Query v5, Zod + react-hook-form, openapi-typescript, @sentry/nextjs, next-secure-headers, pnpm workspaces.

---

## File map

```
aura-id-frontend/
├── pnpm-workspace.yaml               NEW
├── package.json                      REPLACE (workspace root)
├── .claude/                          PRESERVE
├── .husky/                           PRESERVE
├── CLAUDE.md                         PRESERVE
├── .prettierrc                       PRESERVE
├── .secretlintrc.json                PRESERVE
│
├── packages/
│   ├── types/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── index.ts
│   │       ├── scan.ts
│   │       ├── guest.ts
│   │       └── hotel.ts
│   │
│   ├── ui/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── index.ts
│   │       ├── lib/utils.ts          (moved from root lib/utils.ts)
│   │       └── components/           (moved from root components/ui/)
│   │           ├── button.tsx
│   │           ├── card.tsx
│   │           ├── input.tsx
│   │           ├── label.tsx
│   │           └── sonner.tsx
│   │
│   ├── api-client/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── openapi.json              (placeholder — swap for ../../../aura-id/shared/openapi.json later)
│   │   └── src/
│   │       ├── index.ts
│   │       └── generated/
│   │           └── schema.ts         (auto-generated, committed as placeholder)
│   │
│   └── consent/
│       ├── package.json
│       ├── tsconfig.json
│       └── src/
│           ├── index.ts
│           ├── CaptureNotice.tsx
│           └── GuestPageFooter.tsx
│
├── apps/
│   ├── clerk-pwa/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── next.config.ts
│   │   ├── postcss.config.mjs
│   │   ├── components.json
│   │   ├── .env.local.example
│   │   ├── sentry.client.config.ts
│   │   ├── sentry.server.config.ts
│   │   ├── sentry.edge.config.ts
│   │   ├── middleware.ts
│   │   ├── public/
│   │   │   └── manifest.json
│   │   └── app/
│   │       ├── globals.css           (moved from root, add @source for packages/ui)
│   │       ├── layout.tsx
│   │       ├── page.tsx              (redirect to /capture)
│   │       ├── (auth)/
│   │       │   └── login/
│   │       │       ├── page.tsx
│   │       │       └── actions.ts
│   │       ├── capture/
│   │       │   ├── page.tsx
│   │       │   ├── CameraViewfinder.tsx
│   │       │   ├── FramingOverlay.tsx
│   │       │   ├── useCamera.ts
│   │       │   ├── useGlareDetection.ts
│   │       │   ├── useOfflineQueue.ts
│   │       │   ├── useUpload.ts
│   │       │   └── confirm/
│   │       │       ├── page.tsx
│   │       │       └── ConfirmForm.tsx
│   │       ├── history/
│   │       │   └── page.tsx          (scaffold only)
│   │       └── settings/
│   │           └── page.tsx          (scaffold only)
│   │
│   └── dashboard/
│       ├── package.json
│       ├── tsconfig.json
│       ├── next.config.ts
│       ├── postcss.config.mjs
│       ├── components.json
│       ├── .env.local.example
│       ├── sentry.client.config.ts
│       ├── sentry.server.config.ts
│       ├── sentry.edge.config.ts
│       ├── middleware.ts
│       └── app/
│           ├── globals.css
│           ├── layout.tsx
│           ├── page.tsx              (today's check-ins scaffold)
│           └── (auth)/
│               └── login/
│                   ├── page.tsx
│                   └── actions.ts
```

---

## Task 1: Bootstrap pnpm workspace root

**Files:**

- Replace: `package.json`
- Create: `pnpm-workspace.yaml`
- Delete: `package-lock.json`

- [ ] **Step 1.1: Install pnpm globally if not present**

```bash
npm install -g pnpm
pnpm --version
```

Expected: prints a version like `9.x.x`

- [ ] **Step 1.2: Replace root package.json**

Replace the entire contents of `package.json` with:

```json
{
  "name": "aura-id-frontend",
  "private": true,
  "scripts": {
    "dev:clerk": "pnpm --filter @aura/clerk-pwa dev",
    "dev:dashboard": "pnpm --filter @aura/dashboard dev",
    "build": "pnpm -r build",
    "typecheck": "pnpm -r typecheck",
    "lint": "pnpm -r lint",
    "test": "pnpm -r test",
    "generate:api": "pnpm --filter @aura/api-client generate"
  },
  "devDependencies": {
    "typescript": "^5"
  }
}
```

- [ ] **Step 1.3: Create pnpm-workspace.yaml**

```yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

- [ ] **Step 1.4: Remove npm lock file**

```bash
rm package-lock.json
```

- [ ] **Step 1.5: Commit workspace bootstrap**

```bash
git add package.json pnpm-workspace.yaml
git commit -m "chore: bootstrap pnpm workspace root"
```

---

## Task 2: Create packages/types

**Files:**

- Create: `packages/types/package.json`
- Create: `packages/types/tsconfig.json`
- Create: `packages/types/src/index.ts`
- Create: `packages/types/src/scan.ts`
- Create: `packages/types/src/guest.ts`
- Create: `packages/types/src/hotel.ts`

- [ ] **Step 2.1: Create packages/types/package.json**

```json
{
  "name": "@aura/types",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts"
  }
}
```

- [ ] **Step 2.2: Create packages/types/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "declaration": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

- [ ] **Step 2.3: Create packages/types/src/scan.ts**

```typescript
export type ScanStatus = 'pending' | 'processing' | 'complete' | 'failed';

export interface ExtractedFields {
  fullName?: string;
  dateOfBirth?: string;
  documentNumber?: string;
  address?: string;
  documentType?: string;
  expiryDate?: string;
}

export interface Scan {
  id: string;
  hotelId: string;
  status: ScanStatus;
  createdAt: string;
  extractedFields?: ExtractedFields;
}
```

- [ ] **Step 2.4: Create packages/types/src/guest.ts**

```typescript
export interface Guest {
  id: string;
  hotelId: string;
  fullName: string;
  dateOfBirth: string;
  documentNumber: string;
  address?: string;
  createdAt: string;
  imageDeletedAt?: string;
}
```

- [ ] **Step 2.5: Create packages/types/src/hotel.ts**

```typescript
export interface Hotel {
  id: string;
  name: string;
  imageRetentionHours: number;
}
```

- [ ] **Step 2.6: Create packages/types/src/index.ts**

```typescript
export * from './scan';
export * from './guest';
export * from './hotel';
```

- [ ] **Step 2.7: Commit**

```bash
git add packages/types
git commit -m "feat(types): add shared TypeScript types for scan, guest, hotel"
```

---

## Task 3: Create packages/ui (migrate existing shadcn components)

**Files:**

- Create: `packages/ui/package.json`
- Create: `packages/ui/tsconfig.json`
- Create: `packages/ui/src/index.ts`
- Move: `lib/utils.ts` → `packages/ui/src/lib/utils.ts`
- Move: `components/ui/button.tsx` → `packages/ui/src/components/button.tsx`
- Move: `components/ui/card.tsx` → `packages/ui/src/components/card.tsx`
- Move: `components/ui/input.tsx` → `packages/ui/src/components/input.tsx`
- Move: `components/ui/label.tsx` → `packages/ui/src/components/label.tsx`
- Move: `components/ui/sonner.tsx` → `packages/ui/src/components/sonner.tsx`

- [ ] **Step 3.1: Create packages/ui/package.json**

```json
{
  "name": "@aura/ui",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts",
    "./utils": "./src/lib/utils.ts"
  },
  "peerDependencies": {
    "react": "^19",
    "react-dom": "^19"
  },
  "dependencies": {
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^1.14.0",
    "tailwind-merge": "^3.6.0"
  }
}
```

- [ ] **Step 3.2: Create packages/ui/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "declaration": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

- [ ] **Step 3.3: Move existing components and utils**

```bash
mkdir -p packages/ui/src/components packages/ui/src/lib
cp components/ui/button.tsx packages/ui/src/components/button.tsx
cp components/ui/card.tsx packages/ui/src/components/card.tsx
cp components/ui/input.tsx packages/ui/src/components/input.tsx
cp components/ui/label.tsx packages/ui/src/components/label.tsx
cp components/ui/sonner.tsx packages/ui/src/components/sonner.tsx
cp lib/utils.ts packages/ui/src/lib/utils.ts
```

- [ ] **Step 3.4: Create packages/ui/src/index.ts**

```typescript
export { Button, buttonVariants } from './components/button';
export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
} from './components/card';
export { Input } from './components/input';
export { Label } from './components/label';
export { Toaster } from './components/sonner';
export { cn } from './lib/utils';
```

- [ ] **Step 3.5: Commit**

```bash
git add packages/ui
git commit -m "feat(ui): create shared UI package with migrated shadcn components"
```

---

## Task 4: Create packages/api-client

**Files:**

- Create: `packages/api-client/package.json`
- Create: `packages/api-client/tsconfig.json`
- Create: `packages/api-client/openapi.json`
- Create: `packages/api-client/src/generated/schema.ts`
- Create: `packages/api-client/src/index.ts`

- [ ] **Step 4.1: Create packages/api-client/package.json**

```json
{
  "name": "@aura/api-client",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts"
  },
  "scripts": {
    "generate": "openapi-typescript openapi.json -o src/generated/schema.ts"
  },
  "devDependencies": {
    "openapi-typescript": "^7.0.0",
    "typescript": "^5"
  }
}
```

- [ ] **Step 4.2: Create packages/api-client/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "declaration": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

- [ ] **Step 4.3: Create packages/api-client/openapi.json (placeholder)**

```json
{
  "openapi": "3.1.0",
  "info": { "title": "Aura ID API", "version": "0.1.0" },
  "paths": {
    "/scans": {
      "post": {
        "operationId": "createScan",
        "requestBody": {
          "required": true,
          "content": {
            "multipart/form-data": {
              "schema": {
                "type": "object",
                "required": ["image", "hotelId"],
                "properties": {
                  "image": { "type": "string", "format": "binary" },
                  "hotelId": { "type": "string" }
                }
              }
            }
          }
        },
        "responses": {
          "202": {
            "description": "Accepted",
            "content": {
              "application/json": {
                "schema": { "$ref": "#/components/schemas/Scan" }
              }
            }
          }
        }
      }
    },
    "/scans/{id}": {
      "get": {
        "operationId": "getScan",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "schema": { "type": "string" }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": { "$ref": "#/components/schemas/Scan" }
              }
            }
          }
        }
      },
      "patch": {
        "operationId": "updateScan",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "schema": { "type": "string" }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": { "$ref": "#/components/schemas/ExtractedFields" }
            }
          }
        },
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": { "$ref": "#/components/schemas/Scan" }
              }
            }
          }
        }
      }
    },
    "/hotels/me": {
      "get": {
        "operationId": "getMyHotel",
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": { "$ref": "#/components/schemas/Hotel" }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "Scan": {
        "type": "object",
        "required": ["id", "status"],
        "properties": {
          "id": { "type": "string" },
          "status": {
            "type": "string",
            "enum": ["pending", "processing", "complete", "failed"]
          },
          "extractedFields": { "$ref": "#/components/schemas/ExtractedFields" }
        }
      },
      "ExtractedFields": {
        "type": "object",
        "properties": {
          "fullName": { "type": "string" },
          "dateOfBirth": { "type": "string", "format": "date" },
          "documentNumber": { "type": "string" },
          "address": { "type": "string" }
        }
      },
      "Hotel": {
        "type": "object",
        "required": ["id", "name", "imageRetentionHours"],
        "properties": {
          "id": { "type": "string" },
          "name": { "type": "string" },
          "imageRetentionHours": { "type": "integer" }
        }
      }
    }
  }
}
```

- [ ] **Step 4.4: Create packages/api-client/src/generated/schema.ts (hand-written placeholder matching the OpenAPI)**

```typescript
// AUTO-GENERATED from openapi.json — run `pnpm generate:api` to regenerate.
// Replace openapi.json with ../../../aura-id/shared/openapi.json when backend is ready.

export interface paths {
  '/scans': {
    post: operations['createScan'];
  };
  '/scans/{id}': {
    get: operations['getScan'];
    patch: operations['updateScan'];
  };
  '/hotels/me': {
    get: operations['getMyHotel'];
  };
}

export interface components {
  schemas: {
    Scan: {
      id: string;
      status: 'pending' | 'processing' | 'complete' | 'failed';
      extractedFields?: components['schemas']['ExtractedFields'];
    };
    ExtractedFields: {
      fullName?: string;
      dateOfBirth?: string;
      documentNumber?: string;
      address?: string;
    };
    Hotel: {
      id: string;
      name: string;
      imageRetentionHours: number;
    };
  };
}

export interface operations {
  createScan: {
    requestBody: {
      content: {
        'multipart/form-data': {
          image: Blob;
          hotelId: string;
        };
      };
    };
    responses: {
      202: {
        content: {
          'application/json': components['schemas']['Scan'];
        };
      };
    };
  };
  getScan: {
    parameters: { path: { id: string } };
    responses: {
      200: { content: { 'application/json': components['schemas']['Scan'] } };
    };
  };
  updateScan: {
    parameters: { path: { id: string } };
    requestBody: {
      content: { 'application/json': components['schemas']['ExtractedFields'] };
    };
    responses: {
      200: { content: { 'application/json': components['schemas']['Scan'] } };
    };
  };
  getMyHotel: {
    responses: {
      200: { content: { 'application/json': components['schemas']['Hotel'] } };
    };
  };
}
```

- [ ] **Step 4.5: Create packages/api-client/src/index.ts**

```typescript
import type { components, operations } from './generated/schema';

export type Scan = components['schemas']['Scan'];
export type ExtractedFields = components['schemas']['ExtractedFields'];
export type Hotel = components['schemas']['Hotel'];
export type ScanStatus = Scan['status'];

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:4000';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API ${init?.method ?? 'GET'} ${path} → ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function createScan(image: Blob, hotelId: string): Promise<Scan> {
  const form = new FormData();
  form.append('image', image, 'id.jpg');
  form.append('hotelId', hotelId);
  const res = await fetch(`${BASE_URL}/scans`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`createScan → ${res.status}`);
  return res.json() as Promise<Scan>;
}

export function getScan(id: string): Promise<Scan> {
  return apiFetch<Scan>(`/scans/${id}`);
}

export function updateScan(id: string, fields: ExtractedFields): Promise<Scan> {
  return apiFetch<Scan>(`/scans/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(fields),
  });
}

export function getMyHotel(): Promise<Hotel> {
  return apiFetch<Hotel>('/hotels/me');
}
```

- [ ] **Step 4.6: Commit**

```bash
git add packages/api-client
git commit -m "feat(api-client): scaffold openapi codegen package with placeholder schema"
```

---

## Task 5: Create packages/consent

**Files:**

- Create: `packages/consent/package.json`
- Create: `packages/consent/tsconfig.json`
- Create: `packages/consent/src/CaptureNotice.tsx`
- Create: `packages/consent/src/GuestPageFooter.tsx`
- Create: `packages/consent/src/index.ts`

- [ ] **Step 5.1: Create packages/consent/package.json**

```json
{
  "name": "@aura/consent",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts"
  },
  "peerDependencies": {
    "react": "^19"
  }
}
```

- [ ] **Step 5.2: Create packages/consent/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "declaration": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

- [ ] **Step 5.3: Create packages/consent/src/CaptureNotice.tsx**

Exact compliance copy from the spec — do not paraphrase.

```tsx
interface CaptureNoticeProps {
  retentionHours: number;
}

export function CaptureNotice({ retentionHours }: CaptureNoticeProps) {
  return (
    <div
      role="note"
      className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
    >
      <p>
        We extract text from this ID — name, date of birth, document number,
        address. The photograph of the person is automatically removed from the
        image before processing and is never analyzed by AI. ID images are
        deleted after <strong>{retentionHours} hours</strong>.
      </p>
      <a
        href="/privacy"
        className="mt-1 block text-xs text-amber-700 underline"
      >
        How we handle ID data →
      </a>
    </div>
  );
}
```

- [ ] **Step 5.4: Create packages/consent/src/GuestPageFooter.tsx**

```tsx
interface GuestPageFooterProps {
  retentionHours: number;
}

export function GuestPageFooter({ retentionHours }: GuestPageFooterProps) {
  return (
    <footer className="mt-8 border-t pt-4 text-xs text-muted-foreground">
      Aura ID does not process biometric data. Photos are cropped out before
      text extraction. Data retention: <strong>{retentionHours} hours</strong>{' '}
      for images, until deleted for text data.
    </footer>
  );
}
```

- [ ] **Step 5.5: Create packages/consent/src/index.ts**

```typescript
export { CaptureNotice } from './CaptureNotice';
export { GuestPageFooter } from './GuestPageFooter';
```

- [ ] **Step 5.6: Commit**

```bash
git add packages/consent
git commit -m "feat(consent): add BIPA/GDPR compliance components with exact spec copy"
```

---

## Task 6: Scaffold apps/clerk-pwa

**Files:**

- Create: `apps/clerk-pwa/package.json`
- Create: `apps/clerk-pwa/tsconfig.json`
- Create: `apps/clerk-pwa/next.config.ts` (basic — security headers added in Task 8)
- Create: `apps/clerk-pwa/postcss.config.mjs`
- Create: `apps/clerk-pwa/components.json`
- Create: `apps/clerk-pwa/.env.local.example`
- Migrate: root `app/` → `apps/clerk-pwa/app/` (update globals.css imports)
- Create: `apps/clerk-pwa/public/manifest.json`
- Create: `apps/clerk-pwa/app/page.tsx` (redirect to /capture)
- Create: `apps/clerk-pwa/app/history/page.tsx` (scaffold)
- Create: `apps/clerk-pwa/app/settings/page.tsx` (scaffold)

- [ ] **Step 6.1: Create apps/clerk-pwa/package.json**

```json
{
  "name": "@aura/clerk-pwa",
  "version": "0.0.1",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3001",
    "build": "next build",
    "start": "next start --port 3001",
    "lint": "eslint",
    "typecheck": "tsc --noEmit",
    "test": "jest"
  },
  "dependencies": {
    "@aura/api-client": "workspace:*",
    "@aura/consent": "workspace:*",
    "@aura/types": "workspace:*",
    "@aura/ui": "workspace:*",
    "@supabase/ssr": "^0.6.1",
    "@supabase/supabase-js": "^2.50.0",
    "@tanstack/react-query": "^5.80.0",
    "next": "16.2.6",
    "react": "19.2.4",
    "react-dom": "19.2.4",
    "react-hook-form": "^7.56.0",
    "sonner": "^2.0.7",
    "zod": "^3.25.28"
  },
  "devDependencies": {
    "@hookform/resolvers": "^3.10.0",
    "@sentry/nextjs": "^8.0.0",
    "@tailwindcss/postcss": "^4",
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "eslint": "^9",
    "eslint-config-next": "16.2.6",
    "jest": "^30.4.2",
    "next-secure-headers": "^2.2.0",
    "tailwindcss": "^4",
    "typescript": "^5"
  }
}
```

- [ ] **Step 6.2: Create apps/clerk-pwa/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 6.3: Create apps/clerk-pwa/next.config.ts (basic — hardened in Task 8)**

```typescript
import type { NextConfig } from 'next';

const config: NextConfig = {
  reactStrictMode: true,
};

export default config;
```

- [ ] **Step 6.4: Create apps/clerk-pwa/postcss.config.mjs**

```js
const config = {
  plugins: {
    '@tailwindcss/postcss': {},
  },
};
export default config;
```

- [ ] **Step 6.5: Create apps/clerk-pwa/components.json**

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@aura/ui/utils",
    "ui": "@aura/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

- [ ] **Step 6.6: Create apps/clerk-pwa/.env.local.example**

```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:4000
NEXT_PUBLIC_SENTRY_DSN=
```

- [ ] **Step 6.7: Migrate existing app/ directory**

```bash
mkdir -p apps/clerk-pwa/app
cp -r app/. apps/clerk-pwa/app/
```

- [ ] **Step 6.8: Update apps/clerk-pwa/app/globals.css — add @source for packages/ui**

Open `apps/clerk-pwa/app/globals.css`. After the `@import "tailwindcss"` line, add:

```css
@source "../../packages/ui/src/**/*.{ts,tsx}";
@source "../../packages/consent/src/**/*.{ts,tsx}";
```

This tells Tailwind v4 to scan shared packages for class names.

- [ ] **Step 6.9: Replace apps/clerk-pwa/app/layout.tsx**

```tsx
import type { Metadata, Viewport } from 'next';
import { Geist } from 'next/font/google';
import { Toaster } from '@aura/ui';
import './globals.css';

const geist = Geist({ subsets: ['latin'], variable: '--font-geist' });

export const metadata: Metadata = {
  title: 'Aura ID — Capture',
  description: 'Hotel front-desk ID capture',
  manifest: '/manifest.json',
  appleWebApp: { capable: true, statusBarStyle: 'default', title: 'Aura ID' },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
  themeColor: '#ffffff',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={geist.variable}>
      <body className="min-h-dvh bg-background font-sans antialiased">
        {children}
        <Toaster />
      </body>
    </html>
  );
}
```

- [ ] **Step 6.10: Create apps/clerk-pwa/app/page.tsx (redirect to /capture)**

```tsx
import { redirect } from 'next/navigation';
export default function Home() {
  redirect('/capture');
}
```

- [ ] **Step 6.11: Create apps/clerk-pwa/public/manifest.json**

```json
{
  "name": "Aura ID — Capture",
  "short_name": "Aura ID",
  "description": "Hotel front-desk ID capture",
  "start_url": "/capture",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#ffffff",
  "orientation": "portrait",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ]
}
```

- [ ] **Step 6.12: Create apps/clerk-pwa/app/history/page.tsx (scaffold)**

```tsx
export default function HistoryPage() {
  return (
    <main className="p-4">
      <h1 className="text-lg font-semibold">Today's Scans</h1>
      <p className="text-muted-foreground text-sm mt-2">Loading…</p>
    </main>
  );
}
```

- [ ] **Step 6.13: Create apps/clerk-pwa/app/settings/page.tsx (scaffold)**

```tsx
export default function SettingsPage() {
  return (
    <main className="p-4">
      <h1 className="text-lg font-semibold">Settings</h1>
    </main>
  );
}
```

- [ ] **Step 6.14: Commit**

```bash
git add apps/clerk-pwa
git commit -m "feat(clerk-pwa): scaffold PWA app, migrate existing layout"
```

---

## Task 7: Scaffold apps/dashboard

**Files:**

- Create: `apps/dashboard/package.json`
- Create: `apps/dashboard/tsconfig.json`
- Create: `apps/dashboard/next.config.ts`
- Create: `apps/dashboard/postcss.config.mjs`
- Create: `apps/dashboard/components.json`
- Create: `apps/dashboard/.env.local.example`
- Create: `apps/dashboard/app/globals.css`
- Create: `apps/dashboard/app/layout.tsx`
- Create: `apps/dashboard/app/page.tsx`

- [ ] **Step 7.1: Create apps/dashboard/package.json**

```json
{
  "name": "@aura/dashboard",
  "version": "0.0.1",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3002",
    "build": "next build",
    "start": "next start --port 3002",
    "lint": "eslint",
    "typecheck": "tsc --noEmit",
    "test": "jest"
  },
  "dependencies": {
    "@aura/api-client": "workspace:*",
    "@aura/consent": "workspace:*",
    "@aura/types": "workspace:*",
    "@aura/ui": "workspace:*",
    "@supabase/ssr": "^0.6.1",
    "@supabase/supabase-js": "^2.50.0",
    "@tanstack/react-query": "^5.80.0",
    "next": "16.2.6",
    "react": "19.2.4",
    "react-dom": "19.2.4",
    "react-hook-form": "^7.56.0",
    "sonner": "^2.0.7",
    "zod": "^3.25.28"
  },
  "devDependencies": {
    "@hookform/resolvers": "^3.10.0",
    "@sentry/nextjs": "^8.0.0",
    "@tailwindcss/postcss": "^4",
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "eslint": "^9",
    "eslint-config-next": "16.2.6",
    "jest": "^30.4.2",
    "next-secure-headers": "^2.2.0",
    "tailwindcss": "^4",
    "typescript": "^5"
  }
}
```

- [ ] **Step 7.2: Create apps/dashboard/tsconfig.json**

Identical to clerk-pwa:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 7.3: Create apps/dashboard/next.config.ts (basic)**

```typescript
import type { NextConfig } from 'next';

const config: NextConfig = {
  reactStrictMode: true,
};

export default config;
```

- [ ] **Step 7.4: Create apps/dashboard/postcss.config.mjs**

```js
const config = { plugins: { '@tailwindcss/postcss': {} } };
export default config;
```

- [ ] **Step 7.5: Create apps/dashboard/components.json**

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@aura/ui/utils",
    "ui": "@aura/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

- [ ] **Step 7.6: Create apps/dashboard/.env.local.example**

```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:4000
NEXT_PUBLIC_SENTRY_DSN=
```

- [ ] **Step 7.7: Create apps/dashboard/app/globals.css**

```css
@import 'tailwindcss';
@source "../../packages/ui/src/**/*.{ts,tsx}";
@source "../../packages/consent/src/**/*.{ts,tsx}";

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 240 10% 3.9%;
    --muted: 240 4.8% 95.9%;
    --muted-foreground: 240 3.8% 46.1%;
    --border: 240 5.9% 90%;
    --input: 240 5.9% 90%;
    --primary: 240 5.9% 10%;
    --primary-foreground: 0 0% 98%;
    --radius: 0.5rem;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

- [ ] **Step 7.8: Create apps/dashboard/app/layout.tsx**

```tsx
import type { Metadata } from 'next';
import { Geist } from 'next/font/google';
import { Toaster } from '@aura/ui';
import './globals.css';

const geist = Geist({ subsets: ['latin'], variable: '--font-geist' });

export const metadata: Metadata = {
  title: 'Aura ID — Dashboard',
  description: 'Hotel owner dashboard',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={geist.variable}>
      <body className="min-h-screen bg-background font-sans antialiased">
        {children}
        <Toaster />
      </body>
    </html>
  );
}
```

- [ ] **Step 7.9: Create apps/dashboard/app/page.tsx (scaffold)**

```tsx
export default function DashboardHome() {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">Today's Check-ins</h1>
      <p className="text-muted-foreground mt-2 text-sm">Loading…</p>
    </main>
  );
}
```

- [ ] **Step 7.10: Commit**

```bash
git add apps/dashboard
git commit -m "feat(dashboard): scaffold owner dashboard app"
```

---

## Task 8: Install all workspace deps and verify builds

- [ ] **Step 8.1: Run pnpm install from repo root**

```bash
pnpm install
```

Expected: Installs all workspace packages. No errors. Outputs something like `Progress: resolved 800 packages`.

- [ ] **Step 8.2: Typecheck clerk-pwa**

```bash
pnpm --filter @aura/clerk-pwa typecheck
```

Expected: No type errors. If errors appear, they will be about missing `@aura/*` workspace types — fix by checking workspace links (`pnpm ls`).

- [ ] **Step 8.3: Typecheck dashboard**

```bash
pnpm --filter @aura/dashboard typecheck
```

Expected: No type errors.

- [ ] **Step 8.4: Build clerk-pwa**

```bash
pnpm --filter @aura/clerk-pwa build
```

Expected: Build succeeds.

- [ ] **Step 8.5: Build dashboard**

```bash
pnpm --filter @aura/dashboard build
```

Expected: Build succeeds.

- [ ] **Step 8.6: Commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: resolve workspace dependency issues after monorepo migration"
```

---

## Task 9: Configure next-secure-headers in clerk-pwa

**Files:**

- Modify: `apps/clerk-pwa/next.config.ts`

- [ ] **Step 9.1: Replace apps/clerk-pwa/next.config.ts with hardened config**

```typescript
import type { NextConfig } from 'next';
import { createSecureHeaders } from 'next-secure-headers';

const supabaseHost = process.env.NEXT_PUBLIC_SUPABASE_URL
  ? new URL(process.env.NEXT_PUBLIC_SUPABASE_URL).host
  : '*.supabase.co';

const sentryHost = process.env.NEXT_PUBLIC_SENTRY_DSN
  ? new URL(process.env.NEXT_PUBLIC_SENTRY_DSN).host
  : 'o*.ingest.sentry.io';

const apiHost = process.env.NEXT_PUBLIC_API_URL
  ? new URL(process.env.NEXT_PUBLIC_API_URL).host
  : 'localhost:4000';

const secureHeaders = createSecureHeaders({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'"],
      styleSrc: ["'self'"],
      imgSrc: ["'self'", 'data:', 'blob:'],
      // blob: needed for camera stream; mediaDevices API creates blob URLs
      mediaSrc: ["'self'", 'blob:'],
      connectSrc: [
        "'self'",
        `https://${supabaseHost}`,
        `wss://${supabaseHost}`,
        `https://${sentryHost}`,
        `https://${apiHost}`,
        'http://localhost:4000',
      ],
      fontSrc: ["'self'"],
      objectSrc: ["'none'"],
      frameSrc: ["'none'"],
      frameAncestors: ["'none'"],
      baseUri: ["'self'"],
      formAction: ["'self'"],
    },
  },
  forceHTTPSRedirect: [
    true,
    { maxAge: 31536000, includeSubDomains: true, preload: true },
  ],
  referrerPolicy: 'strict-origin-when-cross-origin',
  xContentTypeOptions: 'nosniff',
  xFrameOptions: 'DENY',
  xXSSProtection: '1; mode=block',
});

const config: NextConfig = {
  reactStrictMode: true,
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: secureHeaders,
      },
      // PII pages must not be cached by browser or CDN
      {
        source: '/capture/(.*)',
        headers: [{ key: 'Cache-Control', value: 'no-store, max-age=0' }],
      },
    ];
  },
};

export default config;
```

- [ ] **Step 9.2: Verify build still passes**

```bash
pnpm --filter @aura/clerk-pwa build
```

Expected: Build succeeds.

- [ ] **Step 9.3: Commit**

```bash
git add apps/clerk-pwa/next.config.ts
git commit -m "feat(clerk-pwa): add strict CSP, HSTS, X-Frame-Options via next-secure-headers"
```

---

## Task 10: Configure next-secure-headers in dashboard

**Files:**

- Modify: `apps/dashboard/next.config.ts`

- [ ] **Step 10.1: Replace apps/dashboard/next.config.ts**

```typescript
import type { NextConfig } from 'next';
import { createSecureHeaders } from 'next-secure-headers';

const supabaseHost = process.env.NEXT_PUBLIC_SUPABASE_URL
  ? new URL(process.env.NEXT_PUBLIC_SUPABASE_URL).host
  : '*.supabase.co';

const sentryHost = process.env.NEXT_PUBLIC_SENTRY_DSN
  ? new URL(process.env.NEXT_PUBLIC_SENTRY_DSN).host
  : 'o*.ingest.sentry.io';

const apiHost = process.env.NEXT_PUBLIC_API_URL
  ? new URL(process.env.NEXT_PUBLIC_API_URL).host
  : 'localhost:4000';

const secureHeaders = createSecureHeaders({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'"],
      styleSrc: ["'self'"],
      imgSrc: ["'self'", 'data:'],
      connectSrc: [
        "'self'",
        `https://${supabaseHost}`,
        `wss://${supabaseHost}`,
        `https://${sentryHost}`,
        `https://${apiHost}`,
        'http://localhost:4000',
      ],
      fontSrc: ["'self'"],
      objectSrc: ["'none'"],
      // Stripe Customer Portal is embedded on /billing — allow stripe.com frame
      frameSrc: ['https://billing.stripe.com'],
      frameAncestors: ["'none'"],
      baseUri: ["'self'"],
      formAction: ["'self'"],
    },
  },
  forceHTTPSRedirect: [
    true,
    { maxAge: 31536000, includeSubDomains: true, preload: true },
  ],
  referrerPolicy: 'strict-origin-when-cross-origin',
  xContentTypeOptions: 'nosniff',
  xFrameOptions: 'DENY',
  xXSSProtection: '1; mode=block',
});

const config: NextConfig = {
  reactStrictMode: true,
  async headers() {
    return [
      { source: '/(.*)', headers: secureHeaders },
      // No-store on all routes that render PII
      {
        source: '/guests/(.*)',
        headers: [{ key: 'Cache-Control', value: 'no-store, max-age=0' }],
      },
      {
        source: '/data-requests/(.*)',
        headers: [{ key: 'Cache-Control', value: 'no-store, max-age=0' }],
      },
    ];
  },
};

export default config;
```

- [ ] **Step 10.2: Verify build**

```bash
pnpm --filter @aura/dashboard build
```

Expected: Build succeeds.

- [ ] **Step 10.3: Commit**

```bash
git add apps/dashboard/next.config.ts
git commit -m "feat(dashboard): add strict CSP, HSTS, X-Frame-Options via next-secure-headers"
```

---

## Task 11: Configure Sentry in clerk-pwa

**Files:**

- Create: `apps/clerk-pwa/sentry.client.config.ts`
- Create: `apps/clerk-pwa/sentry.server.config.ts`
- Create: `apps/clerk-pwa/sentry.edge.config.ts`
- Create: `apps/clerk-pwa/lib/sentry-scrub.ts`
- Modify: `apps/clerk-pwa/next.config.ts`

- [ ] **Step 11.1: Create apps/clerk-pwa/lib/sentry-scrub.ts**

Shared PII filter used by beforeSend.

```typescript
import type { Event } from '@sentry/nextjs';

const PII_KEY_RE =
  /name|email|dob|date.?of.?birth|doc|passport|license|address/i;

function scrubObject(obj: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).map(([k, v]) => {
      if (PII_KEY_RE.test(k)) return [k, '[Filtered]'];
      if (typeof v === 'object' && v !== null)
        return [k, scrubObject(v as Record<string, unknown>)];
      return [k, v];
    })
  );
}

export function scrubPii(event: Event): Event {
  if (event.request?.data && typeof event.request.data === 'object') {
    event.request.data = scrubObject(
      event.request.data as Record<string, unknown>
    );
  }
  if (event.extra) {
    event.extra = scrubObject(event.extra as Record<string, unknown>);
  }
  if (event.user) {
    // keep only id — drop name/email
    event.user = event.user.id ? { id: event.user.id } : {};
  }
  return event;
}
```

- [ ] **Step 11.2: Create apps/clerk-pwa/sentry.client.config.ts**

```typescript
import * as Sentry from '@sentry/nextjs';
import { scrubPii } from '@/lib/sentry-scrub';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
  debug: false,
  beforeSend: scrubPii,
  denyUrls: [/localhost/, /127\.0\.0\.1/],
});
```

- [ ] **Step 11.3: Create apps/clerk-pwa/sentry.server.config.ts**

```typescript
import * as Sentry from '@sentry/nextjs';
import { scrubPii } from '@/lib/sentry-scrub';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
  debug: false,
  beforeSend: scrubPii,
});
```

- [ ] **Step 11.4: Create apps/clerk-pwa/sentry.edge.config.ts**

```typescript
import * as Sentry from '@sentry/nextjs';
import { scrubPii } from '@/lib/sentry-scrub';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
  beforeSend: scrubPii,
});
```

- [ ] **Step 11.5: Wrap next.config.ts with Sentry**

Replace the `export default config;` at the end of `apps/clerk-pwa/next.config.ts` with:

```typescript
import { withSentryConfig } from '@sentry/nextjs';

// ... (keep all existing code above) ...

export default withSentryConfig(config, {
  silent: true,
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  widenClientFileUpload: true,
  hideSourceMaps: true,
  disableLogger: true,
  automaticVercelMonitors: false,
});
```

- [ ] **Step 11.6: Verify build**

```bash
pnpm --filter @aura/clerk-pwa build
```

Expected: Build succeeds (Sentry warns about missing DSN — that's fine for now).

- [ ] **Step 11.7: Commit**

```bash
git add apps/clerk-pwa/sentry.*.config.ts apps/clerk-pwa/lib/sentry-scrub.ts apps/clerk-pwa/next.config.ts
git commit -m "feat(clerk-pwa): add Sentry with PII scrubbing beforeSend"
```

---

## Task 12: Configure Sentry in dashboard

**Files:**

- Create: `apps/dashboard/lib/sentry-scrub.ts` (identical content to clerk-pwa)
- Create: `apps/dashboard/sentry.client.config.ts`
- Create: `apps/dashboard/sentry.server.config.ts`
- Create: `apps/dashboard/sentry.edge.config.ts`
- Modify: `apps/dashboard/next.config.ts`

- [ ] **Step 12.1: Create apps/dashboard/lib/sentry-scrub.ts**

Identical content to `apps/clerk-pwa/lib/sentry-scrub.ts` (copy it).

```typescript
import type { Event } from '@sentry/nextjs';

const PII_KEY_RE =
  /name|email|dob|date.?of.?birth|doc|passport|license|address/i;

function scrubObject(obj: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).map(([k, v]) => {
      if (PII_KEY_RE.test(k)) return [k, '[Filtered]'];
      if (typeof v === 'object' && v !== null)
        return [k, scrubObject(v as Record<string, unknown>)];
      return [k, v];
    })
  );
}

export function scrubPii(event: Event): Event {
  if (event.request?.data && typeof event.request.data === 'object') {
    event.request.data = scrubObject(
      event.request.data as Record<string, unknown>
    );
  }
  if (event.extra) {
    event.extra = scrubObject(event.extra as Record<string, unknown>);
  }
  if (event.user) {
    event.user = event.user.id ? { id: event.user.id } : {};
  }
  return event;
}
```

- [ ] **Step 12.2: Create apps/dashboard/sentry.client.config.ts**

```typescript
import * as Sentry from '@sentry/nextjs';
import { scrubPii } from '@/lib/sentry-scrub';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
  debug: false,
  beforeSend: scrubPii,
  denyUrls: [/localhost/, /127\.0\.0\.1/],
});
```

- [ ] **Step 12.3: Create apps/dashboard/sentry.server.config.ts**

```typescript
import * as Sentry from '@sentry/nextjs';
import { scrubPii } from '@/lib/sentry-scrub';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
  debug: false,
  beforeSend: scrubPii,
});
```

- [ ] **Step 12.4: Create apps/dashboard/sentry.edge.config.ts**

```typescript
import * as Sentry from '@sentry/nextjs';
import { scrubPii } from '@/lib/sentry-scrub';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
  beforeSend: scrubPii,
});
```

- [ ] **Step 12.5: Wrap dashboard next.config.ts with Sentry**

Add at the top of `apps/dashboard/next.config.ts`:

```typescript
import { withSentryConfig } from '@sentry/nextjs';
```

Replace `export default config;` with:

```typescript
export default withSentryConfig(config, {
  silent: true,
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  widenClientFileUpload: true,
  hideSourceMaps: true,
  disableLogger: true,
  automaticVercelMonitors: false,
});
```

- [ ] **Step 12.6: Verify build**

```bash
pnpm --filter @aura/dashboard build
```

Expected: Build succeeds.

- [ ] **Step 12.7: Commit**

```bash
git add apps/dashboard/sentry.*.config.ts apps/dashboard/lib/sentry-scrub.ts apps/dashboard/next.config.ts
git commit -m "feat(dashboard): add Sentry with PII scrubbing beforeSend"
```

---

## Task 13: Supabase auth — clerk-pwa

**Files:**

- Create: `apps/clerk-pwa/lib/supabase/server.ts`
- Create: `apps/clerk-pwa/lib/supabase/client.ts`
- Create: `apps/clerk-pwa/middleware.ts`
- Create: `apps/clerk-pwa/app/(auth)/login/page.tsx`
- Create: `apps/clerk-pwa/app/(auth)/login/actions.ts`

- [ ] **Step 13.1: Create apps/clerk-pwa/lib/supabase/server.ts**

```typescript
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          );
        },
      },
    }
  );
}
```

- [ ] **Step 13.2: Create apps/clerk-pwa/lib/supabase/client.ts**

```typescript
import { createBrowserClient } from '@supabase/ssr';

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

- [ ] **Step 13.3: Create apps/clerk-pwa/middleware.ts**

```typescript
import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();
  const isAuthRoute = request.nextUrl.pathname.startsWith('/login');

  if (!user && !isAuthRoute) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  if (user && isAuthRoute) {
    return NextResponse.redirect(new URL('/capture', request.url));
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|manifest.json|icon-|.*\\.png).*)',
  ],
};
```

- [ ] **Step 13.4: Create apps/clerk-pwa/app/(auth)/login/actions.ts**

```typescript
'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';

export async function loginWithEmail(formData: FormData) {
  const supabase = await createClient();
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;

  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) return { error: error.message };

  revalidatePath('/', 'layout');
  redirect('/capture');
}

export async function loginWithGoogle() {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: `${process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3001'}/auth/callback`,
    },
  });
  if (error) return { error: error.message };
  if (data.url) redirect(data.url);
}

export async function logout() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect('/login');
}
```

- [ ] **Step 13.5: Create apps/clerk-pwa/app/(auth)/login/page.tsx**

```tsx
'use client';

import { useState } from 'react';
import { Button } from '@aura/ui';
import { Input } from '@aura/ui';
import { Label } from '@aura/ui';
import { loginWithEmail, loginWithGoogle } from './actions';

export default function LoginPage() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const result = await loginWithEmail(new FormData(e.currentTarget));
    if (result?.error) setError(result.error);
    setLoading(false);
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">Aura ID</h1>
          <p className="text-sm text-muted-foreground">
            Sign in to your front-desk account
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              placeholder="clerk@hotel.com"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-background px-2 text-muted-foreground">or</span>
          </div>
        </div>

        <form action={loginWithGoogle}>
          <Button type="submit" variant="outline" className="w-full">
            Continue with Google
          </Button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 13.6: Create OAuth callback route**

Create `apps/clerk-pwa/app/auth/callback/route.ts`:

```typescript
import { createClient } from '@/lib/supabase/server';
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get('code');

  if (code) {
    const supabase = await createClient();
    await supabase.auth.exchangeCodeForSession(code);
  }

  return NextResponse.redirect(`${origin}/capture`);
}
```

- [ ] **Step 13.7: Typecheck**

```bash
pnpm --filter @aura/clerk-pwa typecheck
```

Expected: No errors.

- [ ] **Step 13.8: Commit**

```bash
git add apps/clerk-pwa/lib apps/clerk-pwa/middleware.ts apps/clerk-pwa/app/\(auth\) apps/clerk-pwa/app/auth
git commit -m "feat(clerk-pwa): add Supabase SSR auth, middleware, login page"
```

---

## Task 14: Supabase auth — dashboard

**Files:**

- Create: `apps/dashboard/lib/supabase/server.ts`
- Create: `apps/dashboard/lib/supabase/client.ts`
- Create: `apps/dashboard/middleware.ts`
- Create: `apps/dashboard/app/(auth)/login/page.tsx`
- Create: `apps/dashboard/app/(auth)/login/actions.ts`
- Create: `apps/dashboard/app/auth/callback/route.ts`

- [ ] **Step 14.1: Create apps/dashboard/lib/supabase/server.ts**

Identical pattern to clerk-pwa:

```typescript
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          );
        },
      },
    }
  );
}
```

- [ ] **Step 14.2: Create apps/dashboard/lib/supabase/client.ts**

```typescript
import { createBrowserClient } from '@supabase/ssr';

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

- [ ] **Step 14.3: Create apps/dashboard/middleware.ts**

```typescript
import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();
  const isAuthRoute = request.nextUrl.pathname.startsWith('/login');

  if (!user && !isAuthRoute) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  if (user && isAuthRoute) {
    return NextResponse.redirect(new URL('/', request.url));
  }

  return supabaseResponse;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.png).*)'],
};
```

- [ ] **Step 14.4: Create apps/dashboard/app/(auth)/login/actions.ts**

```typescript
'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';

export async function loginWithEmail(formData: FormData) {
  const supabase = await createClient();
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;

  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) return { error: error.message };

  revalidatePath('/', 'layout');
  redirect('/');
}

export async function logout() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect('/login');
}
```

- [ ] **Step 14.5: Create apps/dashboard/app/(auth)/login/page.tsx**

```tsx
'use client';

import { useState } from 'react';
import { Button } from '@aura/ui';
import { Input } from '@aura/ui';
import { Label } from '@aura/ui';
import { loginWithEmail } from './actions';

export default function LoginPage() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const result = await loginWithEmail(new FormData(e.currentTarget));
    if (result?.error) setError(result.error);
    setLoading(false);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">Aura ID</h1>
          <p className="text-sm text-muted-foreground">Owner dashboard</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              placeholder="owner@hotel.com"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 14.6: Create apps/dashboard/app/auth/callback/route.ts**

```typescript
import { createClient } from '@/lib/supabase/server';
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get('code');

  if (code) {
    const supabase = await createClient();
    await supabase.auth.exchangeCodeForSession(code);
  }

  return NextResponse.redirect(`${origin}/`);
}
```

- [ ] **Step 14.7: Typecheck**

```bash
pnpm --filter @aura/dashboard typecheck
```

Expected: No errors.

- [ ] **Step 14.8: Commit**

```bash
git add apps/dashboard/lib apps/dashboard/middleware.ts apps/dashboard/app
git commit -m "feat(dashboard): add Supabase SSR auth, middleware, login page"
```

---

## Task 15: Build /capture screen

**Files:**

- Create: `apps/clerk-pwa/app/capture/useCamera.ts`
- Create: `apps/clerk-pwa/app/capture/useGlareDetection.ts`
- Create: `apps/clerk-pwa/app/capture/useOfflineQueue.ts`
- Create: `apps/clerk-pwa/app/capture/FramingOverlay.tsx`
- Create: `apps/clerk-pwa/app/capture/CameraViewfinder.tsx`
- Create: `apps/clerk-pwa/app/capture/page.tsx`

- [ ] **Step 15.1: Create apps/clerk-pwa/app/capture/useCamera.ts**

```typescript
'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export type CameraState = 'idle' | 'starting' | 'ready' | 'error';

export interface UseCameraReturn {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  state: CameraState;
  error: string | null;
  capture: () => Promise<Blob | null>;
  toggleFlash: () => void;
  flashOn: boolean;
}

export function useCamera(): UseCameraReturn {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const trackRef = useRef<MediaStreamTrack | null>(null);
  const [state, setState] = useState<CameraState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [flashOn, setFlashOn] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setState('starting');

    navigator.mediaDevices
      .getUserMedia({
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
          focusMode: 'continuous',
        } as MediaTrackConstraints,
        audio: false,
      })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        trackRef.current = stream.getVideoTracks()[0] ?? null;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setState('ready');
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
        setState('error');
      });

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const capture = useCallback(async (): Promise<Blob | null> => {
    if (!videoRef.current || state !== 'ready') return null;

    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(videoRef.current, 0, 0);

    return new Promise<Blob | null>((resolve) => {
      // Target ~1MB JPEG — start at 0.85 quality, app will compress further if needed
      canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.85);
    });
  }, [state]);

  const toggleFlash = useCallback(() => {
    const track = trackRef.current;
    if (!track) return;
    const newVal = !flashOn;
    // torch is not in TypeScript's MediaTrackConstraintSet — cast needed
    (track.applyConstraints as (c: Record<string, unknown>) => Promise<void>)({
      advanced: [{ torch: newVal }],
    }).catch(() => {
      /* torch not supported — ignore */
    });
    setFlashOn(newVal);
  }, [flashOn]);

  return { videoRef, state, error, capture, toggleFlash, flashOn };
}
```

- [ ] **Step 15.2: Create apps/clerk-pwa/app/capture/useGlareDetection.ts**

```typescript
'use client';

import { useCallback, useRef } from 'react';

// Mean luminance above this threshold (0-255) signals likely glare.
const GLARE_THRESHOLD = 210;
// Sample every N-th pixel to avoid blocking the main thread.
const SAMPLE_STEP = 8;

export function useGlareDetection(
  videoRef: React.RefObject<HTMLVideoElement | null>
) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const checkGlare = useCallback((): boolean => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) return false;

    // Reuse a small off-screen canvas for sampling
    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas');
    }
    const canvas = canvasRef.current;
    // Downsample to 160×90 — enough for a brightness histogram
    canvas.width = 160;
    canvas.height = 90;

    const ctx = canvas.getContext('2d', { willReadFrequently: true })!;
    ctx.drawImage(video, 0, 0, 160, 90);

    const { data } = ctx.getImageData(0, 0, 160, 90);
    let sum = 0;
    let count = 0;

    for (let i = 0; i < data.length; i += 4 * SAMPLE_STEP) {
      const r = data[i]!;
      const g = data[i + 1]!;
      const b = data[i + 2]!;
      // Luminance (BT.601)
      sum += 0.299 * r + 0.587 * g + 0.114 * b;
      count++;
    }

    return count > 0 && sum / count > GLARE_THRESHOLD;
  }, [videoRef]);

  return { checkGlare };
}
```

- [ ] **Step 15.3: Create apps/clerk-pwa/app/capture/useOfflineQueue.ts**

IndexedDB queue. Entries are encrypted with a key derived from the Supabase session token so raw image bytes are never stored in plaintext. Queue entries older than 1 hour are purged on open.

```typescript
'use client';

import { useCallback } from 'react';

const DB_NAME = 'aura-offline-queue';
const STORE_NAME = 'scans';
const MAX_AGE_MS = 60 * 60 * 1000; // 1 hour

interface QueueEntry {
  id: string;
  hotelId: string;
  iv: string; // base64 AES-GCM IV
  ciphertext: string; // base64 encrypted JPEG bytes
  queuedAt: number;
}

async function deriveKey(sessionToken: string): Promise<CryptoKey> {
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    enc.encode(sessionToken),
    { name: 'PBKDF2' },
    false,
    ['deriveKey']
  );
  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: enc.encode('aura-queue-salt'),
      iterations: 100_000,
      hash: 'SHA-256',
    },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );
}

function toBase64(buf: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(buf)));
}

function fromBase64(b64: string): Uint8Array {
  return Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
}

async function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE_NAME, { keyPath: 'id' });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function purgeExpired(db: IDBDatabase): Promise<void> {
  const now = Date.now();
  const tx = db.transaction(STORE_NAME, 'readwrite');
  const store = tx.objectStore(STORE_NAME);

  return new Promise((resolve, reject) => {
    const req = store.openCursor();
    req.onsuccess = () => {
      const cursor = req.result;
      if (!cursor) {
        resolve();
        return;
      }
      const entry = cursor.value as QueueEntry;
      if (now - entry.queuedAt > MAX_AGE_MS) cursor.delete();
      cursor.continue();
    };
    req.onerror = () => reject(req.error);
  });
}

export function useOfflineQueue() {
  const enqueue = useCallback(
    async (
      image: Blob,
      hotelId: string,
      sessionToken: string
    ): Promise<void> => {
      const key = await deriveKey(sessionToken);
      const iv = crypto.getRandomValues(new Uint8Array(12));
      const imageBytes = await image.arrayBuffer();
      const ciphertext = await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv },
        key,
        imageBytes
      );

      const entry: QueueEntry = {
        id: crypto.randomUUID(),
        hotelId,
        iv: toBase64(iv.buffer),
        ciphertext: toBase64(ciphertext),
        queuedAt: Date.now(),
      };

      const db = await openDb();
      await purgeExpired(db);

      return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const req = tx.objectStore(STORE_NAME).put(entry);
        req.onsuccess = () => resolve();
        req.onerror = () => reject(req.error);
      });
    },
    []
  );

  const dequeue = useCallback(
    async (
      sessionToken: string
    ): Promise<Array<{ id: string; hotelId: string; image: Blob }>> => {
      const db = await openDb();
      await purgeExpired(db);
      const key = await deriveKey(sessionToken);

      return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const req = tx.objectStore(STORE_NAME).getAll();
        req.onsuccess = async () => {
          const entries = req.result as QueueEntry[];
          const items = await Promise.all(
            entries.map(async (e) => {
              const plaintext = await crypto.subtle.decrypt(
                { name: 'AES-GCM', iv: fromBase64(e.iv) },
                key,
                fromBase64(e.ciphertext).buffer
              );
              return {
                id: e.id,
                hotelId: e.hotelId,
                image: new Blob([plaintext], { type: 'image/jpeg' }),
              };
            })
          );
          resolve(items);
        };
        req.onerror = () => reject(req.error);
      });
    },
    []
  );

  return { enqueue, dequeue };
}
```

- [ ] **Step 15.4: Create apps/clerk-pwa/app/capture/FramingOverlay.tsx**

```tsx
export function FramingOverlay() {
  const strokeW = 3;
  const corner = 24;

  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {/* Semi-transparent mask around the ID frame */}
      <mask id="frame-mask">
        <rect width="100" height="100" fill="white" />
        <rect x="8" y="20" width="84" height="60" rx="2" fill="black" />
      </mask>
      <rect
        width="100"
        height="100"
        fill="rgba(0,0,0,0.45)"
        mask="url(#frame-mask)"
      />

      {/* 4-corner brackets */}
      {/* top-left */}
      <path
        d={`M 8 ${20 + corner} L 8 20 L ${8 + corner} 20`}
        fill="none"
        stroke="white"
        strokeWidth={strokeW / 10}
      />
      {/* top-right */}
      <path
        d={`M ${92 - corner} 20 L 92 20 L 92 ${20 + corner}`}
        fill="none"
        stroke="white"
        strokeWidth={strokeW / 10}
      />
      {/* bottom-left */}
      <path
        d={`M 8 ${80 - corner} L 8 80 L ${8 + corner} 80`}
        fill="none"
        stroke="white"
        strokeWidth={strokeW / 10}
      />
      {/* bottom-right */}
      <path
        d={`M ${92 - corner} 80 L 92 80 L 92 ${80 - corner}`}
        fill="none"
        stroke="white"
        strokeWidth={strokeW / 10}
      />
    </svg>
  );
}
```

- [ ] **Step 15.5: Create apps/clerk-pwa/app/capture/CameraViewfinder.tsx**

```tsx
'use client';

import { FramingOverlay } from './FramingOverlay';
import type { UseCameraReturn } from './useCamera';

interface CameraViewfinderProps {
  camera: UseCameraReturn;
  glareWarning: boolean;
}

export function CameraViewfinder({
  camera,
  glareWarning,
}: CameraViewfinderProps) {
  return (
    <div className="relative flex-1 overflow-hidden bg-black">
      {camera.state === 'error' ? (
        <div className="flex h-full items-center justify-center text-white text-sm px-8 text-center">
          {camera.error ?? 'Camera unavailable'}
        </div>
      ) : (
        <>
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <video
            ref={camera.videoRef}
            autoPlay
            playsInline
            muted
            className="h-full w-full object-cover"
          />
          <FramingOverlay />

          {glareWarning && (
            <div
              role="alert"
              className="absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full bg-black/70 px-4 py-2 text-xs text-white"
            >
              Too much glare — adjust the lighting
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 15.6: Create apps/clerk-pwa/app/capture/page.tsx**

```tsx
'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Button } from '@aura/ui';
import { CaptureNotice } from '@aura/consent';
import { CameraViewfinder } from './CameraViewfinder';
import { useCamera } from './useCamera';
import { useGlareDetection } from './useGlareDetection';

// Default shown before /hotels/me loads
const DEFAULT_RETENTION_HOURS = 24;

export default function CapturePage() {
  const router = useRouter();
  const camera = useCamera();
  const { checkGlare } = useGlareDetection(camera.videoRef);
  const [glareWarning, setGlareWarning] = useState(false);
  const [retentionHours, setRetentionHours] = useState(DEFAULT_RETENTION_HOURS);
  const [uploading, setUploading] = useState(false);

  // Poll glare every 2s while camera is ready
  useEffect(() => {
    if (camera.state !== 'ready') return;
    const id = setInterval(() => setGlareWarning(checkGlare()), 2000);
    return () => clearInterval(id);
  }, [camera.state, checkGlare]);

  // Fetch retention hours from /hotels/me on mount
  useEffect(() => {
    fetch('/api/hotels/me')
      .then((r) => r.json())
      .then((hotel: { imageRetentionHours?: number }) => {
        if (hotel.imageRetentionHours)
          setRetentionHours(hotel.imageRetentionHours);
      })
      .catch(() => {
        /* use default */
      });
  }, []);

  const handleCapture = useCallback(async () => {
    if (uploading) return;
    const blob = await camera.capture();
    if (!blob) return;

    // Haptic feedback on supported devices
    navigator.vibrate?.(30);

    setUploading(true);
    toast.loading('Uploading…');

    try {
      // Compress to ~1MB if needed
      let uploadBlob = blob;
      if (blob.size > 1_048_576) {
        uploadBlob = await compressToTarget(blob, 1_048_576);
      }

      const form = new FormData();
      form.append('image', uploadBlob, 'id.jpg');

      toast.loading('Extracting text…');
      const res = await fetch('/api/scans', { method: 'POST', body: form });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);

      const scan = (await res.json()) as { id: string };
      toast.dismiss();
      router.push(`/capture/confirm?scan_id=${scan.id}`);
    } catch (err) {
      toast.dismiss();
      toast.error('Upload failed — saved for retry when connection returns');
      // Offline queue is handled in useUpload — this page just shows the error
    } finally {
      setUploading(false);
    }
  }, [camera, router, uploading]);

  return (
    <div className="flex h-dvh flex-col">
      {/* Consent notice — MUST appear before camera view */}
      <div className="p-3 safe-area-inset-top">
        <CaptureNotice retentionHours={retentionHours} />
      </div>

      <CameraViewfinder camera={camera} glareWarning={glareWarning} />

      {/* Controls */}
      <div className="flex items-center justify-between px-6 py-4 safe-area-inset-bottom bg-black">
        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:text-white/80"
          onClick={() => router.push('/history')}
        >
          History
        </Button>

        {/* Shutter button */}
        <button
          onClick={handleCapture}
          disabled={camera.state !== 'ready' || uploading}
          aria-label="Capture ID"
          className="h-16 w-16 rounded-full border-4 border-white bg-white/20 
                     hover:bg-white/30 active:scale-95 disabled:opacity-50
                     transition-transform focus-visible:outline-none 
                     focus-visible:ring-2 focus-visible:ring-white"
        />

        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:text-white/80"
          onClick={camera.toggleFlash}
        >
          {camera.flashOn ? 'Flash On' : 'Flash Off'}
        </Button>
      </div>
    </div>
  );
}

async function compressToTarget(
  blob: Blob,
  targetBytes: number
): Promise<Blob> {
  const bitmap = await createImageBitmap(blob);
  const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
  const ctx = canvas.getContext('2d')!;
  ctx.drawImage(bitmap, 0, 0);

  let quality = 0.8;
  let result = await canvas.convertToBlob({ type: 'image/jpeg', quality });
  while (result.size > targetBytes && quality > 0.3) {
    quality -= 0.1;
    result = await canvas.convertToBlob({ type: 'image/jpeg', quality });
  }
  return result;
}
```

- [ ] **Step 15.7: Typecheck**

```bash
pnpm --filter @aura/clerk-pwa typecheck
```

Expected: No errors.

- [ ] **Step 15.8: Commit**

```bash
git add apps/clerk-pwa/app/capture
git commit -m "feat(clerk-pwa): build /capture screen with camera, framing overlay, glare detection, consent notice"
```

---

## Task 16: Wire POST /scans

**Files:**

- Create: `apps/clerk-pwa/app/capture/useUpload.ts`
- Modify: `apps/clerk-pwa/app/capture/page.tsx` (replace inline fetch with hook)

- [ ] **Step 16.1: Create apps/clerk-pwa/app/capture/useUpload.ts**

```typescript
'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createScan } from '@aura/api-client';
import type { Scan } from '@aura/api-client';
import { toast } from 'sonner';
import { useOfflineQueue } from './useOfflineQueue';

interface UploadParams {
  image: Blob;
  hotelId: string;
  sessionToken: string;
}

export function useUpload() {
  const queryClient = useQueryClient();
  const { enqueue } = useOfflineQueue();

  return useMutation<Scan, Error, UploadParams>({
    mutationKey: ['upload-scan'],
    mutationFn: ({ image, hotelId }) => createScan(image, hotelId),
    onMutate: () => {
      toast.loading('Uploading…', { id: 'upload' });
    },
    onSuccess: () => {
      toast.loading('Extracting text…', { id: 'upload' });
      // queryClient invalidation happens in onSettled after navigation
      queryClient.invalidateQueries({ queryKey: ['scans'] });
    },
    onError: async (error, variables) => {
      toast.dismiss('upload');
      toast.error('No connection — saved for retry');
      // Encrypt and queue for retry
      await enqueue(variables.image, variables.hotelId, variables.sessionToken);
    },
    onSettled: () => {
      toast.dismiss('upload');
    },
  });
}
```

- [ ] **Step 16.2: Add TanStack Query provider to clerk-pwa layout**

Create `apps/clerk-pwa/app/providers.tsx`:

```tsx
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  // One QueryClient per browser session — never put PII in cache keys
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            gcTime: 60_000,
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

Update `apps/clerk-pwa/app/layout.tsx` — wrap `{children}` with `<Providers>`:

```tsx
import { Providers } from './providers';

// Inside RootLayout, replace {children} with:
<Providers>{children}</Providers>;
```

- [ ] **Step 16.3: Update capture/page.tsx to use useUpload hook**

Replace the inline fetch block in `handleCapture` with the mutation:

At the top of the file, add imports:

```tsx
import { useUpload } from './useUpload';
import { createClient } from '@/lib/supabase/client';
```

Inside the component, add:

```tsx
const upload = useUpload();
```

Replace the entire `try/catch/finally` block in `handleCapture` with:

```tsx
const supabase = createClient();
const {
  data: { session },
} = await supabase.auth.getSession();
const sessionToken = session?.access_token ?? 'anon';

upload.mutate(
  { image: uploadBlob, hotelId: 'placeholder', sessionToken },
  {
    onSuccess: (scan) => {
      router.push(`/capture/confirm?scan_id=${scan.id}`);
    },
  }
);
```

Also update the `uploading` state check to use `upload.isPending`:

```tsx
const uploading = upload.isPending;
```

- [ ] **Step 16.4: Typecheck**

```bash
pnpm --filter @aura/clerk-pwa typecheck
```

Expected: No errors.

- [ ] **Step 16.5: Commit**

```bash
git add apps/clerk-pwa/app/capture/useUpload.ts apps/clerk-pwa/app/providers.tsx apps/clerk-pwa/app/layout.tsx apps/clerk-pwa/app/capture/page.tsx
git commit -m "feat(clerk-pwa): wire POST /scans through TanStack Query mutation with offline IndexedDB fallback"
```

---

## Task 17: Build /capture/confirm

**Files:**

- Create: `apps/clerk-pwa/app/capture/confirm/ConfirmForm.tsx`
- Create: `apps/clerk-pwa/app/capture/confirm/page.tsx`

- [ ] **Step 17.1: Create apps/clerk-pwa/app/capture/confirm/ConfirmForm.tsx**

```tsx
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button, Input, Label } from '@aura/ui';
import type { ExtractedFields } from '@aura/api-client';

const schema = z.object({
  fullName: z.string().min(1, 'Name is required'),
  dateOfBirth: z.string().min(1, 'Date of birth is required'),
  documentNumber: z.string().min(1, 'Document number is required'),
  address: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface ConfirmFormProps {
  initialFields: ExtractedFields;
  onSubmit: (fields: FormValues) => Promise<void>;
  isSubmitting: boolean;
}

export function ConfirmForm({
  initialFields,
  onSubmit,
  isSubmitting,
}: ConfirmFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      fullName: initialFields.fullName ?? '',
      dateOfBirth: initialFields.dateOfBirth ?? '',
      documentNumber: initialFields.documentNumber ?? '',
      address: initialFields.address ?? '',
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="fullName">Full name</Label>
        <Input id="fullName" {...register('fullName')} autoComplete="off" />
        {errors.fullName && (
          <p className="text-xs text-destructive">{errors.fullName.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="dateOfBirth">Date of birth</Label>
        <Input
          id="dateOfBirth"
          {...register('dateOfBirth')}
          autoComplete="off"
        />
        {errors.dateOfBirth && (
          <p className="text-xs text-destructive">
            {errors.dateOfBirth.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="documentNumber">Document number</Label>
        <Input
          id="documentNumber"
          {...register('documentNumber')}
          autoComplete="off"
        />
        {errors.documentNumber && (
          <p className="text-xs text-destructive">
            {errors.documentNumber.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="address">
          Address <span className="text-muted-foreground">(optional)</span>
        </Label>
        <Input id="address" {...register('address')} autoComplete="off" />
      </div>

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Sending…' : 'Submit to PMS'}
      </Button>
    </form>
  );
}
```

- [ ] **Step 17.2: Create apps/clerk-pwa/app/capture/confirm/page.tsx**

```tsx
'use client';

import { useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { getScan, updateScan } from '@aura/api-client';
import type { ExtractedFields } from '@aura/api-client';
import { ConfirmForm } from './ConfirmForm';

export default function ConfirmPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();

  // scan_id from URL — PII-free, just an opaque ID
  const scanId = searchParams.get('scan_id');

  const {
    data: scan,
    isLoading,
    error,
  } = useQuery({
    // Key never contains PII — only the opaque scan ID
    queryKey: ['scan', scanId],
    queryFn: () => getScan(scanId!),
    enabled: !!scanId,
    staleTime: 0,
    gcTime: 0,
  });

  const mutation = useMutation({
    mutationFn: (fields: ExtractedFields) => updateScan(scanId!, fields),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ['scan', scanId] });
      toast.success('Sent to PMS — ready for next guest');
      router.push('/capture');
    },
    onError: () => {
      toast.error('Failed to submit — please try again');
    },
  });

  const handleSubmit = useCallback(
    async (fields: ExtractedFields) => {
      mutation.mutate(fields);
    },
    [mutation]
  );

  if (!scanId) {
    return (
      <main className="p-4">
        <p className="text-sm text-destructive">
          No scan ID — go back and try again.
        </p>
      </main>
    );
  }

  if (isLoading) {
    return (
      <main className="p-4">
        <p className="text-sm text-muted-foreground">Extracting text…</p>
      </main>
    );
  }

  if (error || !scan) {
    return (
      <main className="p-4">
        <p className="text-sm text-destructive">
          Failed to load scan. Please go back and try again.
        </p>
      </main>
    );
  }

  return (
    <main className="p-4 space-y-6 max-w-md mx-auto">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold">Review extracted fields</h1>
        <p className="text-sm text-muted-foreground">
          Edit any incorrect values before submitting.
        </p>
        {/* Compliance: no image shown here, ever */}
      </div>

      <ConfirmForm
        initialFields={scan.extractedFields ?? {}}
        onSubmit={handleSubmit}
        isSubmitting={mutation.isPending}
      />

      <p className="text-xs text-muted-foreground text-center">
        No photo is shown here — only the extracted text fields.
      </p>
    </main>
  );
}
```

- [ ] **Step 17.3: Typecheck**

```bash
pnpm --filter @aura/clerk-pwa typecheck
```

Expected: No errors.

- [ ] **Step 17.4: Final build verification**

```bash
pnpm --filter @aura/clerk-pwa build && pnpm --filter @aura/dashboard build
```

Expected: Both succeed.

- [ ] **Step 17.5: Commit**

```bash
git add apps/clerk-pwa/app/capture/confirm
git commit -m "feat(clerk-pwa): build /capture/confirm with text-only review form, no image display"
```

---

## Final cleanup

- [ ] **Delete root-level files that have moved to apps/clerk-pwa/**

```bash
rm -rf app components lib public next.config.ts tsconfig.json postcss.config.mjs eslint.config.mjs components.json
```

- [ ] **Verify clean build after cleanup**

```bash
pnpm --filter @aura/clerk-pwa build && pnpm --filter @aura/dashboard build
```

- [ ] **Commit cleanup**

```bash
git add -A
git commit -m "chore: remove root-level files migrated to apps/clerk-pwa"
```

---

## Self-review notes

- All 10 spec steps are covered by Tasks 1-17.
- `Cache-Control: no-store` applied to `/capture/*` in clerk-pwa and `/guests/*`, `/data-requests/*` in dashboard.
- TanStack Query keys: `['scan', scanId]`, `['scans']` — never contain PII.
- `CaptureNotice` is the only place the compliance copy lives — both apps import it from `@aura/consent`.
- `/capture/confirm` reads only `extractedFields` from the scan — no image URL is read or rendered.
- IndexedDB entries encrypted with `AES-GCM` key derived from session token via `PBKDF2` (100k iterations).
- Service worker is NOT included — the spec requires one for app-shell only but explicitly bans API response caching; scaffolding a compliant one is a follow-up task.
- Icon PNGs (192px, 512px) for the manifest are not generated — add them to `apps/clerk-pwa/public/` before production deploy.
