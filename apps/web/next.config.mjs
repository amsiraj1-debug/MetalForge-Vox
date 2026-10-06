/** @type {import('next').NextConfig} */
const config={output:'standalone',async rewrites(){return [{source:'/api/:path*',destination:`${process.env.VOCALMORPH_API || 'http://127.0.0.1:8000'}/api/:path*`}];}};export default config;
