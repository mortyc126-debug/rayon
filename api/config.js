// Vercel Serverless Function — returns Supabase public config
// Set environment variables in Vercel → Project Settings → Environment Variables:
//   SUPABASE_URL  = https://ooozuuppbggjwhijbwsr.supabase.co
//   SUPABASE_KEY  = (your anon key)
module.exports = function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store, no-cache');
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_KEY) {
    return res.status(500).json({ error: 'Supabase env vars not set in Vercel' });
  }
  res.status(200).json({
    url: process.env.SUPABASE_URL,
    key: process.env.SUPABASE_KEY,
  });
};
