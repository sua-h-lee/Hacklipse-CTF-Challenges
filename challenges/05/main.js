const express = require('express');
const app = express();

const mysql = require('mysql2/promise');
const flag = process.env.CTF_FLAG_05;
if (!/^HKL\{[^{}\r\n]+\}$/.test(flag || '')) {
    throw new Error('CTF_FLAG_05 must have the form HKL{...}');
}
const db = mysql.createPool({
    host: process.env.DB_HOST || 'localhost',
    port: Number(process.env.DB_PORT || 3306),
    user: process.env.DB_USER || 'challenge',
    password: process.env.DB_PASSWORD || 'challengepass',
    database: process.env.DB_NAME || 'main',
    connectionLimit: 5,
});

const BAN = ['admin', 'hkl', 'admi'];

function filter(data){
    const dump = JSON.stringify(data).toLowerCase();
    return BAN.some(word => dump.includes(word));
}

app.get('/login', async function(req, res) {
    if(filter(req.query)){
        res.send('filter');
        return;
    }
    const {uid, upw} = req.query;
    if (typeof uid !== 'string' || typeof upw !== 'string') {
        res.send('undefined');
        return;
    }

    const query = `SELECT uid, upw FROM users WHERE uid = '${uid}' AND upw = '${upw}' LIMIT 1`;
    try {
        const [rows] = await db.query(query);
        if (!rows.length) {
            res.send('undefined');
        } else if (rows[0].uid === 'admin') {
            res.type('text/plain').send(rows[0].upw);
        } else {
            res.type('text/plain').send(rows[0].uid);
        }
    } catch (err) {
        res.send('err');
    }
});

app.get('/', function(req, res) {
    res.send('login?uid=guest&upw=guest');
});

async function start() {
    await db.execute('INSERT INTO users (uid, upw) VALUES (?, ?) ON DUPLICATE KEY UPDATE upw = VALUES(upw)',
        ['admin', flag]);
    app.listen(8000, '0.0.0.0');
}

start().catch(err => {
    console.error('Failed to initialize challenge database:', err);
    process.exit(1);
});
