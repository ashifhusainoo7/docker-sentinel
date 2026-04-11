export default function CrashDetailPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Crash Detail</h2>
      <p className="text-muted-foreground">
        Detailed crash view with logs, analysis, and actions will be implemented here.
      </p>
    </div>
  );
}
