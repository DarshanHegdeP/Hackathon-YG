require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');
const WebSocket = require('ws');

if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SECRET_KEY) {
  console.warn('⚠️ SUPABASE_URL or SUPABASE_SECRET_KEY missing in .env');
}

const supabase = createClient(
  process.env.SUPABASE_URL || 'https://placeholder.supabase.co',
  process.env.SUPABASE_SECRET_KEY || 'placeholder',
  {
    auth: { persistSession: false },
    realtime: { transport: WebSocket }
  }
);

module.exports = { supabase };
