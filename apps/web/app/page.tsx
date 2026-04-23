import { DashboardView } from "../components/dashboard-view";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function HomePage() {
  return <DashboardView />;
}
