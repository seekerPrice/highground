import type { NextConfig } from "next";
const config: NextConfig = {
  async headers() {
    return [{source:"/report/:path*",headers:[
      {key:"Cache-Control",value:"private, no-store, max-age=0"},
      {key:"Referrer-Policy",value:"no-referrer"},
      {key:"X-Content-Type-Options",value:"nosniff"},
      {key:"Content-Security-Policy",value:"default-src 'self'; script-src 'self' 'unsafe-inline'"+(process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : "")+"; style-src 'self' 'unsafe-inline'; connect-src 'self'; font-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"},
    ]}];
  },
};
export default config;
