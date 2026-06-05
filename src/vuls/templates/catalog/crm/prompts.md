# CRM Template Prompt

Generate a commercial SaaS-quality CRM application using the supplied project brief.
Generate a working Next.js App Router MVP using TypeScript and Tailwind CSS.
Do not create placeholder pages, empty components, lorem ipsum, TODO text, or generic page shells.
The generated app must include real React/Next.js code for these routes:

- `src/app/dashboard/page.tsx`: dashboard metric cards showing total customer count, total order count, open order count and task count.
- `src/app/customers/page.tsx`: Supabase-backed customer list and add-customer form with CRUD controls.
- `src/app/orders/page.tsx`: Supabase-backed order list with service details, dates, prices, CRUD controls and visible order status badges.
- `src/app/tasks/page.tsx`: task board with staff owners, due dates and visible task status.

Do not use mock-data files, hardcoded arrays or local-only state for CRM records.
Use Supabase as the runtime database and include:

- `schema.sql` with `customers`, `orders` and `tasks` tables.
- `env.example` with `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- `src/lib/supabase.ts` with a lazy Supabase client factory.
- Server Actions or server-side handlers for customer CRUD and order CRUD.

Include the required Next.js/Tailwind setup files: `package.json`, `tsconfig.json`, `next.config.ts`, `tailwind.config.ts`, `postcss.config.js`, `src/app/layout.tsx` and `src/app/globals.css`.
Never import from next/router in files under `src/app`; use `next/navigation` for App Router navigation.
Any component that uses React hooks such as `useState`, `useEffect`, `useRouter`, `useSearchParams` or `usePathname` must start with `"use client"`.
Use simple, readable SaaS UI copy directly in the MVP so the app runs without missing translation helpers.
Adapt labels, sample customers, services and orders to the user domain from the brief, for example a car wash CRM should include vehicles, wash services and order statuses.
The README must include overview, features, setup, environment and testing sections.
