import { NextRequest, NextResponse } from 'next/server';

// middleware.ts - Handle legacy route redirects at edge level
export function middleware(request: NextRequest) {
  const url = request.nextUrl.clone();
  const pathname = url.pathname;

  // Legacy Flask route mappings
  const legacyRoutes: Record<string, string> = {
    // Authentication routes
    '/login': '/auth/signin',
    '/register': '/auth/signup',
    '/logout': '/auth/signout',
    
    // Dashboard routes
    '/dashboard': '/dashboard/overview',
    '/dashboard/jobs': '/dashboard/work-requests',
    '/dashboard/profile': '/dashboard/profile',
    '/dashboard/payments': '/dashboard/payments',
    '/dashboard/settings': '/dashboard/settings',
    
    // Profile routes
    '/profile': '/profiles',
    '/contractor': '/professionals',
    '/customer': '/customers',
    
    // Work-related routes
    '/jobs': '/work-requests',
    '/work-request': '/work',
    '/post-job': '/work-requests/new',
    '/find-work': '/work-requests',
    
    // Support routes
    '/help': '/support',
    '/contact': '/support/contact',
    '/faq': '/support/faq',
    
    // Legal routes
    '/terms': '/legal/terms',
    '/privacy': '/legal/privacy',
    '/cookie-policy': '/legal/cookies',
    
    // Admin routes
    '/admin': '/admin/dashboard',
    '/admin/users': '/admin/users',
    '/admin/reports': '/admin/analytics',
  };

  // Check for exact match
  if (legacyRoutes[pathname]) {
    url.pathname = legacyRoutes[pathname];
    return NextResponse.redirect(url, 301);
  }

  // Handle parameterized routes
  const routeEntries = Object.keys(legacyRoutes).map(key => [key, legacyRoutes[key]]);
  for (const [pattern, replacement] of routeEntries) {
    if (pathname.startsWith(pattern + '/')) {
      const param = pathname.substring(pattern.length + 1);
      url.pathname = replacement + '/' + param;
      return NextResponse.redirect(url, 301);
    }
  }

  // Handle API route redirects
  if (pathname.startsWith('/api/v1/')) {
    url.pathname = pathname.replace('/api/v1/', '/api/');
    return NextResponse.redirect(url, 301);
  }

  // Handle static asset redirects
  if (pathname.startsWith('/static/')) {
    url.hostname = 'cdn.laborlooker.com';
    url.pathname = pathname.replace('/static/', '/assets/');
    return NextResponse.redirect(url, 301);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};