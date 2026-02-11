module.exports = {
    apps: [
        {
            name: 'AEGIS-CORE',
            script: 'backend/server.py',
            interpreter: 'python',
            autorestart: true,
            max_memory_restart: '1G',
            out_file: '~/.aegis/logs/combined.log',
            error_file: '~/.aegis/logs/combined.log',
            merge_logs: true,
            env: {
                NODE_ENV: 'development',
            },
            env_production: {
                NODE_ENV: 'production',
            }
        },
        {
            name: 'AEGIS-TELEGRAM',
            script: 'backend/telegram_bridge.py',
            interpreter: 'python',
            autorestart: true,
            max_memory_restart: '500M',
            out_file: '~/.aegis/logs/telegram.log',
            error_file: '~/.aegis/logs/telegram.log',
            merge_logs: true,
            env: {
                NODE_ENV: 'development',
            },
            env_production: {
                NODE_ENV: 'production',
            }
        }
    ]
};
