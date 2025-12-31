# Football Scout Assistant Frontend

This is the Next.js frontend for the football analytics application, built with modern React patterns and interactive data visualizations.

## Tech Stack

- **Framework**: Next.js 14 with App Router and TypeScript
- **Styling**: Tailwind CSS with custom design system
- **UI Components**: shadcn/ui (built on Radix primitives)
- **Charts**: Plotly.js via react-plotly.js for interactive visualizations
- **Data Fetching**: TanStack Query (React Query) with typed API client
- **Design**: Atomic Design methodology (atoms → molecules → organisms → pages)

## Getting Started

### Prerequisites

Make sure the backend API is running first:
```bash
# From project root
docker-compose up -d --build db redis api
```

### Install and Run

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
```bash
# Create .env.local file
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > .env.local
```

3. Start the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Features

- **Rankings Page** (`/rankings`): Interactive player rankings with filters and chart/table views
- **Scatter Plots** (`/scatter`): Compare two metrics across players with interactive visualizations
- **Player Profiles** (`/players/[id]`): Detailed individual player statistics
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Data**: Live connection to FastAPI backend

## Project Structure

```
web/
├── src/
│   ├── app/                 # Next.js App Router pages
│   │   ├── page.tsx         # Home page
│   │   ├── rankings/        # Rankings page
│   │   └── layout.tsx       # Root layout
│   ├── components/          # Reusable UI components
│   │   ├── ui/              # shadcn/ui components
│   │   ├── PlotlyFigure.tsx # Chart rendering component
│   │   └── Navigation.tsx   # App navigation
│   ├── lib/
│   │   └── api.ts           # Typed API client with Zod schemas
│   └── providers/           # React context providers
└── public/                  # Static assets
```

## Key Components

- **PlotlyFigure**: Generic component for rendering Plotly charts from API URLs
- **Navigation**: App-wide navigation component
- **API Client**: Type-safe API client with Zod validation
- **Query Provider**: React Query setup for data caching and synchronization

## Development Notes

- Uses Server Components by default, Client Components only when needed
- All charts are rendered from backend Plotly JSON (no client-side chart building)
- Responsive design with mobile-first approach
- Accessible components with proper ARIA labels and keyboard navigation

## Deployment

For production deployment, build the application:

```bash
npm run build
npm start
```

Or deploy to Vercel/Netlify with automatic builds from your Git repository.
