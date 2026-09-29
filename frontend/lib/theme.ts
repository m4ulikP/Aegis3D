/**
 * Central design tokens for Aegis3D Mission-Critical Structural Engineering Control Center.
 * Merges core theme surfaces, typography, status colors, and responsive spacing tokens.
 */

export const theme = {
    typography: {
        fontSans: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        fontMono: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    },
    surfaces: {
        background: "#080d1a",
        canvas: "#020617",
        card: "#0f172a",
        panel: "rgba(15, 23, 42, 0.88)",
        panelElevated: "rgba(30, 41, 59, 0.75)",
        panelSubtle: "rgba(30, 41, 59, 0.35)",
        border: "rgba(148, 163, 184, 0.18)",
        borderFocus: "rgba(56, 189, 248, 0.60)",
        borderWarning: "rgba(245, 158, 11, 0.50)",
        borderCritical: "rgba(239, 68, 68, 0.50)",
    },
    text: {
        primary: "#f8fafc",
        secondary: "#94a3b8",
        muted: "#64748b",
        accent: "#38bdf8",
    },
    status: {
        normal: {
            bg: "rgba(16, 185, 129, 0.15)",
            text: "#10b981",
            border: "rgba(16, 185, 129, 0.3)",
            solid: "#059669",
            label: "NORMAL",
        },
        monitor: {
            bg: "rgba(59, 130, 246, 0.15)",
            text: "#60a5fa",
            border: "rgba(59, 130, 246, 0.3)",
            solid: "#0284c7",
            label: "MONITOR",
        },
        warning: {
            bg: "rgba(245, 158, 11, 0.15)",
            text: "#f59e0b",
            border: "rgba(245, 158, 11, 0.3)",
            solid: "#d97706",
            label: "WARNING",
        },
        critical: {
            bg: "rgba(239, 68, 68, 0.15)",
            text: "#ef4444",
            border: "rgba(239, 68, 68, 0.3)",
            solid: "#dc2626",
            label: "CRITICAL",
        },
    },
    spacing: {
        xs: 4,
        sm: 8,
        md: 12,
        lg: 16,
        xl: 24,
    },
};
