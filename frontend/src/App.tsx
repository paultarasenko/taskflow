import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Единый QueryClient для всего приложения — TanStack Query кэширует
// серверный стейт (см. docs/01-architecture-and-design.md, раздел 2.4).
const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
        <div className="text-center">
          <h1 className="text-3xl font-semibold tracking-tight">TaskFlow</h1>
          <p className="mt-2 text-slate-400">
            Этап 2 — скелет проекта. UI появится на Этапе 9.
          </p>
        </div>
      </div>
    </QueryClientProvider>
  )
}

export default App
