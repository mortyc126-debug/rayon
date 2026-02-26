// Vercel Serverless Function — verifies Telegram Mini App initData
// TELEGRAM_BOT_TOKEN stays server-side, never sent to browser
//
// POST /api/tg-auth
// Body: { initData: "..." }  (window.Telegram.WebApp.initData)
// Returns: { ok: true, user: { id, first_name, username, ... } }
//       or { ok: false, error: "..." }

const crypto = require('crypto');

module.exports = function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ ok: false, error: 'Method not allowed' });

  const token = process.env.TELEGRAM_BOT_TOKEN;
  if (!token) return res.status(500).json({ ok: false, error: 'TELEGRAM_BOT_TOKEN not set' });

  const { initData } = req.body || {};
  if (!initData) return res.status(400).json({ ok: false, error: 'initData required' });

  try {
    // Parse initData query string
    const params = new URLSearchParams(initData);
    const hash = params.get('hash');
    if (!hash) return res.status(400).json({ ok: false, error: 'hash missing' });

    // Build data-check-string: sorted key=value pairs (excluding hash), joined by \n
    const entries = [...params.entries()]
      .filter(([k]) => k !== 'hash')
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => `${k}=${v}`)
      .join('\n');

    // secret_key = HMAC-SHA256("WebAppData", bot_token)
    const secretKey = crypto.createHmac('sha256', 'WebAppData').update(token).digest();
    // expected = HMAC-SHA256(data-check-string, secret_key)
    const expected = crypto.createHmac('sha256', secretKey).update(entries).digest('hex');

    if (expected !== hash) {
      return res.status(401).json({ ok: false, error: 'Invalid initData signature' });
    }

    // Check expiry (auth_date must be within 24h)
    const authDate = parseInt(params.get('auth_date') || '0', 10);
    if (Date.now() / 1000 - authDate > 86400) {
      return res.status(401).json({ ok: false, error: 'initData expired' });
    }

    const user = JSON.parse(params.get('user') || '{}');
    return res.status(200).json({ ok: true, user });
  } catch (e) {
    return res.status(500).json({ ok: false, error: e.message });
  }
};
