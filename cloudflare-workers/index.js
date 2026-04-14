// Cloudflare Worker for EmailDigest
// This serves as a reverse proxy and can also serve static assets

// Export as a module if this file will be used by Cloudflare Workers
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // Route /api/* requests to backend
    if (url.pathname.startsWith('/api')) {
      const backendUrl = new URL(env.BACKEND_URL + url.pathname + url.search);
      const response = await fetch(backendUrl.toString(), {
        method: request.method,
        headers: {
          'Content-Type': 'application/json',
          ...Object.fromEntries(request.headers),
        },
        body: request.body,
      });
      
      // Add CORS headers
      const corsHeaders = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': '*',
      };
      
      return new Response(response.body, {
        status: response.status,
        headers: { ...corsHeaders, ...Object.fromEntries(response.headers) },
      });
    }
    
    // Route everything else to frontend
    if (url.pathname === '/' || url.pathname.endsWith('.html') || url.pathname.startsWith('/_')) {
      const frontendUrl = new URL(env.FRONTEND_URL + url.pathname + url.search);
      const response = await fetch(frontendUrl.toString());
      return response;
    }
    
    // 404 for everything else
    return new Response('Not Found', { status: 404 });
  },
};
