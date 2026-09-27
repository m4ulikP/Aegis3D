import CityMap from "@/components/dashboard/CityMap";
import MonitoringOverlay from "@/components/dashboard/MonitoringOverlay";

export default function DashboardPage() {
    return (
        <main
            style={{
                position: "relative",
                width: "100vw",
                height: "100vh",
                background: "#111827",
                overflow: "hidden",
            }}
        >
            <MonitoringOverlay />
            <CityMap />
        </main>
    );
}