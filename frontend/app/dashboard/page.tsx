import CityMap from "@/components/dashboard/CityMap";

export default function DashboardPage() {
    return (
        <main
            style={{
                width: "100vw",
                height: "100vh",
                background: "#111827",
            }}
        >
            <CityMap />
        </main>
    );
}