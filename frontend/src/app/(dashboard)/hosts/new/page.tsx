import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AddHostPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h2 className="text-2xl font-bold">Add Docker Host</h2>
      <Card>
        <CardHeader>
          <CardTitle>Connection Mode</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Choose between Direct TCP connection or Agent-based monitoring.
            Form will be implemented here.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
