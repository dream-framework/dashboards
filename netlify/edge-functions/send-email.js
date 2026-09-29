// ════════════════════════════════════════════════════════════════════════════
//  send-email — Netlify Edge Function (Deno runtime)
//
//  Receives contact form submissions from insightanalyticsca.github.io and
//  sends a polished, branded HTML email to dev@insight-analytics.ca via the
//  Resend API (https://resend.com).
//
//  Why Resend:
//   - Free tier: 100 emails/day, 3,000/month (well above demo request volume)
//   - Cleanest API of any email provider — single POST to /emails
//   - Native Deno-friendly (just fetch + Bearer token)
//   - Supports reply-to so you can hit "Reply" in your inbox and reach the
//     visitor directly
//
//  Setup (one-time):
//   1. Sign up at https://resend.com (free, 1 minute)
//   2. Verify your domain (insight-analytics.ca) by adding the SPF + DKIM
//      DNS records Resend shows you. (You can skip this for testing — Resend
//      gives you an onboarding@resend.dev "from" address that can send to
//      your account email only.)
//   3. Generate an API key at https://resend.com/api-keys
//   4. On Netlify, set the env var:
//        RESEND_API_KEY = re_...your key...
//      (Site settings → Environment variables → Add a variable)
//   5. Trigger a redeploy. The endpoint becomes:
//        https://dashboards-groq-proxy.netlify.app/send-email
//
//  CORS: allows insightanalyticsca.github.io + localhost dev origins.
//
//  Rate limit: 5 submissions per IP per hour (in-memory, per edge instance).
//  This protects against casual abuse; serious flood protection needs a
//  shared store (Netlify Blobs).
//
//  If RESEND_API_KEY is not set, the endpoint returns 503 — the client-side
//  JS in /insight-analytics/js/app.js catches this and falls back to the
//  polished plain-text mailto: version so the form still works.
// ════════════════════════════════════════════════════════════════════════════

const RESEND_URL = 'https://api.resend.com/emails';

// From address — uses the verified domain. If the domain isn't verified yet,
// set FROM_EMAIL = 'Insight Analytics <onboarding@resend.dev>' and the email
// will only deliver to your Resend account email (good for testing).
const FROM_EMAIL = 'Insight Analytics <noreply@insight-analytics.ca>';
const TO_EMAIL = 'dev@insight-analytics.ca';

const ALLOWED_ORIGINS = [
  'https://insight-analytics.ca',
  'https://www.insight-analytics.ca',
  'https://insightanalyticsca.github.io',
  'http://localhost:3000',
  'http://127.0.0.1:3000',
  'http://localhost:5173',
  'http://127.0.0.1:5173'
];

function corsHeaders(origin) {
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    'Access-Control-Allow-Origin': allow,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin'
  };
}

// ─── Rate limit (in-memory, per edge instance) ──────────────────────────────
const rate = new Map();
const RATE_LIMIT = 5;
const RATE_WINDOW_MS = 60 * 60 * 1000;

function rateLimitOk(ip) {
  const now = Date.now();
  const arr = (rate.get(ip) || []).filter(ts => now - ts < RATE_WINDOW_MS);
  if (arr.length >= RATE_LIMIT) return false;
  arr.push(now);
  rate.set(ip, arr);
  return true;
}

// ─── HTML escaping ─────────────────────────────────────────────────────────
function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ─── HTML email template (inline CSS for max client compatibility) ─────────
function buildEmail(data) {
  const name = escapeHtml(data.name || '');
  const email = escapeHtml(data.email || '');
  const company = escapeHtml(data.company || '—');
  const message = escapeHtml(data.message || '');

  // Subject with branded middle-dot + em-dash separators
  const subject = 'Demo Request  ·  ' + data.name +
    (data.company ? '  —  ' + data.company : '');

  // Plain-text fallback (shown by email clients that don't render HTML)
  const text =
    'INSIGHT ANALYTICS  ·  DEMO REQUEST\n\n' +
    'Name:     ' + (data.name || '') + '\n' +
    'Email:    ' + (data.email || '') + '\n' +
    'Company:  ' + (data.company || '—') + '\n\n' +
    'Message:\n' + (data.message || '') + '\n\n' +
    '— ' + '\n' +
    'Sent via insightanalyticsca.github.io/insight-analytics/\n';

  // HTML body — table-based layout, inline CSS only.
  // Works in Gmail (web + app), Outlook (desktop + web), Apple Mail, Yahoo.
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-Content-Type-Options" content="nosniff">
  <title>${subject}</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#0f172a;-webkit-font-smoothing:antialiased;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:24px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px -8px rgba(15,23,42,0.18);">

          <!-- Header — branded gradient bar with IA mark -->
          <tr>
            <td style="background:linear-gradient(135deg,#1E3A8A 0%,#6366F1 55%,#06B6D4 100%);padding:28px 40px;">
              <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td style="vertical-align:middle;">
                    <table role="presentation" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="width:44px;height:44px;background:rgba(255,255,255,0.15);border-radius:12px;text-align:center;vertical-align:middle;color:#ffffff;font-size:18px;font-weight:800;letter-spacing:0.02em;line-height:44px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">IA</td>
                        <td style="padding-left:14px;vertical-align:middle;color:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
                          <div style="font-size:18px;font-weight:800;letter-spacing:-0.01em;line-height:1.2;">Insight Analytics</div>
                          <div style="font-size:11px;opacity:0.85;letter-spacing:0.08em;text-transform:uppercase;margin-top:3px;">New Demo Request</div>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Hero — title + subtitle -->
          <tr>
            <td style="padding:36px 40px 20px 40px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
              <h1 style="margin:0 0 8px 0;font-size:26px;font-weight:800;letter-spacing:-0.02em;line-height:1.2;color:#0f172a;">New demo request</h1>
              <p style="margin:0;font-size:15px;line-height:1.55;color:#475569;">A visitor submitted the contact form on the Insight Analytics marketing site.</p>
            </td>
          </tr>

          <!-- Divider — subtle gradient line -->
          <tr>
            <td style="padding:0 40px 24px 40px;">
              <div style="height:1px;background:linear-gradient(90deg,transparent 0%,#e2e8f0 15%,#e2e8f0 85%,transparent 100%);"></div>
            </td>
          </tr>

          <!-- Spec table — labeled rows -->
          <tr>
            <td style="padding:0 40px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding:10px 0;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#64748b;width:120px;">Name</td>
                  <td style="padding:10px 0;font-size:15px;font-weight:600;color:#0f172a;">${name}</td>
                </tr>
                <tr>
                  <td colspan="2" style="padding:0;"><div style="height:1px;background:#f1f5f9;"></div></td>
                </tr>
                <tr>
                  <td style="padding:10px 0;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#64748b;">Email</td>
                  <td style="padding:10px 0;font-size:15px;font-weight:600;color:#1E3A8A;"><a href="mailto:${email}" style="color:#1E3A8A;text-decoration:none;">${email}</a></td>
                </tr>
                <tr>
                  <td colspan="2" style="padding:0;"><div style="height:1px;background:#f1f5f9;"></div></td>
                </tr>
                <tr>
                  <td style="padding:10px 0;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#64748b;">Company</td>
                  <td style="padding:10px 0;font-size:15px;font-weight:600;color:#0f172a;">${company}</td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Message — soft gradient box -->
          <tr>
            <td style="padding:24px 40px 32px 40px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
              <div style="background:linear-gradient(135deg,rgba(99,102,241,0.05) 0%,rgba(6,182,212,0.03) 100%);border:1px solid #e2e8f0;border-radius:12px;padding:20px 22px;">
                <div style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#64748b;margin-bottom:8px;">Message</div>
                <div style="font-size:14px;line-height:1.65;color:#1e293b;white-space:pre-wrap;">${message}</div>
              </div>
            </td>
          </tr>

          <!-- Footer — dark navy CTA bar -->
          <tr>
            <td style="background:#0f172a;padding:22px 40px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="color:#94a3b8;font-size:12px;line-height:1.65;">
                    Sent via <a href="https://insightanalyticsca.github.io/insight-analytics/" style="color:#06B6D4;text-decoration:none;font-weight:600;">insightanalyticsca.github.io/insight-analytics/</a>
                    <br>
                    Reply directly to this email — the visitor's address is set as Reply-To.
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

  return { subject, html, text };
}

// ─── Main handler ──────────────────────────────────────────────────────────
export default async (request, context) => {
  const origin = request.headers.get('origin') || '';

  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders(origin) });
  }

  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
    });
  }

  // Extract visitor IP for rate-limiting
  const ip = request.headers.get('fastly-client-ip') ||
             (request.headers.get('x-forwarded-for') || '').split(',')[0].trim() ||
             request.headers.get('x-real-ip') ||
             request.headers.get('x-nf-client-connection-ip') ||
             'unknown';
  if (!rateLimitOk(ip)) {
    return new Response(JSON.stringify({ error: 'Rate limit exceeded. Please try again later.' }), {
      status: 429,
      headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
    });
  }

  // Parse JSON body
  let body;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON body' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
    });
  }

  const { name, email, company, message } = body;

  // Validate required fields
  if (!name || !email || !message) {
    return new Response(JSON.stringify({
      error: 'Missing required fields (name, email, message are required)'
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
    });
  }

  // Validate email format
  const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRe.test(email)) {
    return new Response(JSON.stringify({ error: 'Invalid email address' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
    });
  }

  // Check Resend API key
  const RESEND_KEY = Deno.env.get('RESEND_API_KEY');
  if (!RESEND_KEY) {
    return new Response(JSON.stringify({
      error: 'Email service not configured',
      hint: 'Set RESEND_API_KEY env var on Netlify to enable email sending.',
      fallback: 'Client should fall back to mailto:'
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
    });
  }

  // Build email
  const { subject, html, text } = buildEmail({ name, email, company, message });
  const replyTo = `${name} <${email}>`;

  // Send via Resend
  let res;
  try {
    res = await fetch(RESEND_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${RESEND_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        from: FROM_EMAIL,
        to: [TO_EMAIL],
        reply_to: replyTo,
        subject: subject,
        html: html,
        text: text
      })
    });
  } catch (e) {
    return new Response(JSON.stringify({
      error: 'Failed to reach email service',
      detail: e.message
    }), {
      status: 502,
      headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
    });
  }

  if (!res.ok) {
    const errBody = await res.text();
    return new Response(JSON.stringify({
      error: 'Email service returned an error',
      status: res.status,
      detail: errBody.slice(0, 300)
    }), {
      status: 502,
      headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
    });
  }

  const data = await res.json();
  return new Response(JSON.stringify({
    ok: true,
    messageId: data.id || data.data?.id || null
  }), {
    status: 200,
    headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
  });
};

export const config = {
  path: '/send-email'
};
