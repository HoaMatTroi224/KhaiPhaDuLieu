import './globals.css';
import { Inter } from 'next/font/google';

const inter = Inter({ subsets: ['latin'] });

export default function RootLayout({
    children,
} : {
    children: React.ReactNode;
}) 
{
    return (
      <html lang="en" className={inter.className}>
        <body className="bg-gray-50 antialiased">
          {children}  
        </body>
      </html>
    );
}