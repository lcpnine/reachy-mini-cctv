# web — 파일/폴더 구조

```
web/
├── app/
│   ├── layout.tsx          # 루트 레이아웃
│   ├── page.tsx            # Live Feed (/)
│   ├── globals.css
│   ├── components/         # 공용 컴포넌트 (Sidebar 등)
│   ├── users/
│   │   └── page.tsx        # 사용자 관리 (/users)
│   └── photos/
│       └── page.tsx        # 미등록 방문자 갤러리 (/photos)
├── lib/                    # API 클라이언트, 유틸
│   └── api.ts
├── public/
├── .env.local.example
├── package.json
├── next.config.ts
├── tsconfig.json
├── postcss.config.mjs
├── eslint.config.mjs
└── README.md
```
