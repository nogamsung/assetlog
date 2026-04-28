import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import localFont from "next/font/local"; // {/* ADDED */}
import { headers } from "next/headers"; // {/* ADDED */}
import { Providers } from "@/providers";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const pretendard = localFont({ // {/* ADDED */}
  src: "../../public/fonts/PretendardVariable.woff2", // {/* ADDED */}
  variable: "--font-pretendard", // {/* ADDED */}
  display: "swap", // {/* ADDED */}
  weight: "45 920", // {/* ADDED */}
}); // {/* ADDED */}

export const metadata: Metadata = {
  title: "AssetLog",
  description: "개인 포트폴리오 트래커",
};

const themeInitScript = `(function(){try{var s=localStorage.getItem('assetlog-theme');var t=s?JSON.parse(s):null;var theme=t&&t.state&&t.state.theme?t.state.theme:'system';var r=document.documentElement;r.classList.remove('light','dark');if(theme==='light')r.classList.add('light');else if(theme==='dark')r.classList.add('dark');}catch(e){}})();`;

export default async function RootLayout({ // {/* MODIFIED */}
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const headersList = await headers(); // {/* ADDED */}
  const nonce = headersList.get("x-nonce") ?? ""; // {/* ADDED */}

  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} ${pretendard.variable} h-full antialiased`} /* MODIFIED */
      suppressHydrationWarning
    >
      <head>
        <script nonce={nonce} dangerouslySetInnerHTML={{ __html: themeInitScript }} /> {/* MODIFIED */}
      </head>
      <body className="min-h-full flex flex-col">
        <Providers>
          <ThemeProvider>{children}</ThemeProvider>
        </Providers>
      </body>
    </html>
  );
}
