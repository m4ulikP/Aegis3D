import CityMap from "@/components/dashboard/CityMap";
import MonitoringOverlay from "@/components/dashboard/MonitoringOverlay";

export default function DashboardPage() {
    return (
        <main
            style={{
                position: "relative",
                width: "100%",
                height: "100dvh",
                background: "#020617",
                overflow: "hidden",
            }}
        >
            <MonitoringOverlay />
            <CityMap />
        </main>
    );
}