const localtunnel = require('localtunnel');

let currentTunnel = null;

async function startTunnel() {
  try {
    const tunnel = await localtunnel({ port: 3000 });
    currentTunnel = tunnel;
    console.log(`\n==============================================`);
    console.log(`🌐 LIVE PUBLIC URL: ${tunnel.url}`);
    console.log(`==============================================\n`);

    tunnel.on('close', () => {
      console.log('Tunnel closed. Reconnecting in 3s...');
      setTimeout(startTunnel, 3000);
    });

    tunnel.on('error', (err) => {
      console.error('Tunnel error:', err.message);
      setTimeout(startTunnel, 3000);
    });
  } catch (err) {
    console.error('Failed to create tunnel, retrying in 5s...', err.message);
    setTimeout(startTunnel, 5000);
  }
}

startTunnel();
