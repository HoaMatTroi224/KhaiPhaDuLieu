// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { createServerClient, type CookieOptions } from '@supabase/ssr';

export async function proxy(req: NextRequest) {
  let response = NextResponse.next({
    request: { headers: req.headers },
  });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        get(name: string) {
          return req.cookies.get(name)?.value;
        },
        set(name: string, value: string, options: CookieOptions) {
          response.cookies.set({ name, value, ...options });
        },
        remove(name: string, options: CookieOptions) {
          response.cookies.set({ name, value: '', ...options });
        },
      },
    }
  );

  try {
    // Chỉ cần gọi getUser() là đủ
    const {
      data: { user },
    } = await supabase.auth.getUser();

    const pathname = req.nextUrl.pathname;
    const isAuthPage = pathname.startsWith('/auth/login') || pathname.startsWith('/auth/signup');
    const isProtectedRoute =
      pathname.startsWith('/dashboard') ||
      pathname.startsWith('/projects') ||
      pathname.startsWith('/library');

    // Redirect nếu chưa login vào route bảo vệ
    if (!user && isProtectedRoute) {
      const url = new URL('/auth/login', req.url);
      url.searchParams.set('next', pathname); // Lưu lại trang đích
      return NextResponse.redirect(url);
    }

    // Redirect nếu đã login vào trang auth
    if (user && isAuthPage) {
      const next = req.nextUrl.searchParams.get('next');
      return NextResponse.redirect(new URL(next || '/dashboard', req.url));
    }
  } catch (err) {
    console.error('Middleware auth error:', err);
    // Fail-safe: nếu lỗi auth, cho phép tiếp tục (tránh lock user)
    // Hoặc redirect về login nếu muốn strict:
    // return NextResponse.redirect(new URL('/auth/login', req.url));
  }

  return response;
}

// Bật matcher để middleware chỉ chạy ở route cần thiết (tăng performance)
export const config = {
  matcher: [
    '/dashboard/:path*',
    '/projects/:path*',
    '/library/:path*',
    '/auth/login',
    '/auth/signup',
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
