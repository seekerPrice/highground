export default function Dashboard() {
  return (
    <main className="mx-auto min-h-screen max-w-5xl px-6 py-12 sm:px-10">
      <header className="border-b border-emerald-900/15 pb-6">
        <p className="mb-2 text-xs font-semibold tracking-widest uppercase text-emerald-800">
          HighGround
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
      </header>
      <section aria-label="Dashboard status" className="mt-10 rounded-xl border border-emerald-900/15 bg-white p-8">
        <h2 className="text-lg font-medium">Your dashboard starts here.</h2>
        <p className="mt-2 max-w-lg text-sm leading-6 text-slate-600">
          Flood observations and shop activity are not connected yet.
        </p>
      </section>
    </main>
  );
}
