export const metadata = {
  title: "Smart Travel Companion",
  description: "Weather-aware MRT dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
