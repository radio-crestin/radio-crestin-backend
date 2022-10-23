import {NextRequest, NextResponse} from 'next/server';

export function middleware(req: NextRequest) {
  const host: any = req.headers.get('host');
  const cdnRegex = /^cdn\./;
  // This redirect will only take effect on a production website (on a non-localhost domain)
  // @ts-ignore
  if (cdnRegex.test(host) && !req.headers.get('host').includes('localhost')) {
    const newHost = host.replace(cdnRegex, '');
    return NextResponse.redirect(
      `https://www.${newHost}${req.nextUrl.pathname}`,
      301,
    );
  }
  return NextResponse.next();
}
