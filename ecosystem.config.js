module.exports = {
    apps: [
        {
            name: 'ATLAS-CORE',
            script: 'backend/server.py',
            interpreter: 'python',
            autorestart: true,
            max_memory_restart: '1G',
            out_file: '~/.atlas/logs/combined.log',
            error_file: '~/.atlas/logs/combined.log',
            merge_logs: true,
            env: {
                NODE_ENV: 'development',
            },
            env_production: {
                NODE_ENV: 'production',
            }
        },
        {
            name: 'ATLAS-TELEGRAM',
            script: 'backend/telegram_bridge.py',
            interpreter: 'python',
            autorestart: true,
            max_memory_restart: '500M',
            out_file: '~/.atlas/logs/telegram.log',
            error_file: '~/.atlas/logs/telegram.log',
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
