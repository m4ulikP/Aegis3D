import "./globals.css";

export const metadata = {
  title: 'Aegis3D — Structural Health Monitoring',
  description: 'Real-time civil infrastructure telemetry and 3D digital twin visualization',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
