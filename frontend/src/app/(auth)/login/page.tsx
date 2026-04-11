import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">DockerSentinel</CardTitle>
          <CardDescription>
            Multi-Agent Docker Container Crash Monitor
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <a href={`${API_URL}/api/v1/auth/github`}>
            <Button className="w-full" variant="outline">
              Continue with GitHub
            </Button>
          </a>
          <a href={`${API_URL}/api/v1/auth/google`}>
            <Button className="w-full" variant="outline">
              Continue with Google
            </Button>
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
