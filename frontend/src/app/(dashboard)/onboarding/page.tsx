import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function OnboardingPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6 py-12">
      <div className="text-center">
        <h1 className="text-3xl font-bold">Welcome to DockerSentinel</h1>
        <p className="mt-2 text-muted-foreground">
          Let&apos;s get your container monitoring set up in a few steps.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Step 1: Add a Docker Host</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Onboarding wizard will guide through: name workspace, add first Docker host,
            configure notifications.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
