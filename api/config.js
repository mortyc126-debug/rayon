// Vercel Serverless Function — returns public config
// Set in Vercel → Project Settings → Environment Variables:
//   SUPABASE_URL      = https://xxxx.supabase.co
//   SUPABASE_KEY      = (anon key)
//   WEBAPP_URL        = https://rayon-nu.vercel.app
//   TELEGRAM_BOT_TOKEN = (bot token — server-side only, NOT returned here)
module.exports = function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store, no-cache');
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_KEY) {
    return res.status(500).json({ error: 'Supabase env vars not set in Vercel' });
  }
  res.status(200).json({
    url: process.env.SUPABASE_URL,
    key: process.env.SUPABASE_KEY,
    webappUrl: process.env.WEBAPP_URL || '',
  });
};
