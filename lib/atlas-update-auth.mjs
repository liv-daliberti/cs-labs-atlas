// Public viewing does not grant access to maintenance APIs.
// The token is a Sites runtime secret, never a browser or source credential.
export function protectedAtlasUpdate(handler) {
  return async (request, env) => {
    const expected = env.ATLAS_UPDATE_TOKEN;
    const supplied = request.headers.get('X-Atlas-Update-Token');
    let authorized = false;
    if (typeof expected === 'string' && expected.length >= 32 && supplied && supplied.length <= 512) {
      const encode = value => new TextEncoder().encode(value);
      const [a,b] = await Promise.all([expected,supplied].map(value => crypto.subtle.digest('SHA-256',encode(value))));
      const left = new Uint8Array(a), right = new Uint8Array(b);
      let difference = 0;
      for (let i=0;i<left.length;i++) difference |= left[i]^right[i];
      authorized = difference === 0;
    }
    if (!authorized) return Response.json({error:'Update authorization required'}, {
      status:403, headers:{'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'},
    });
    return handler(request,env);
  };
}
