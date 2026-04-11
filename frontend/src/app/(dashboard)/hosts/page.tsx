import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function HostsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Docker Hosts</h2>
        <Link href="/hosts/new">
          <Button>Add Host</Button>
        </Link>
      </div>
      <p className="text-muted-foreground">
        Docker hosts with connection status will be listed here.
      </p>
    </div>
  );
}
