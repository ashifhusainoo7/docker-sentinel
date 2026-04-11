import { NavLinks } from "./nav-links";

export function Sidebar() {
  return (
    <aside className="hidden w-64 border-r bg-background lg:block">
      <div className="flex h-16 items-center border-b px-6">
        <h1 className="text-lg font-bold">DockerSentinel</h1>
      </div>
      <div className="px-4 py-6">
        <NavLinks />
      </div>
    </aside>
  );
}
