import { createServerClient, type CookieOptions } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get('code');
  const nextParam = requestUrl.searchParams.get('next');
  const next = nextParam?.startsWith('/') && !nextParam.startsWith('//') ? nextParam : '/dashboard';
  const redirectUrl = requestUrl.origin + next;

  let response = NextResponse.redirect(redirectUrl);

  if (!code) {
    return response;
  }

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        get(name: string) {
          return request.cookies.get(name)?.value;
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

  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    const errorUrl = new URL('/auth/login', requestUrl.origin);
    errorUrl.searchParams.set('error', 'oauth');
    errorUrl.searchParams.set('message', error.message);
    response = NextResponse.redirect(errorUrl);
  }

  return response;
}
