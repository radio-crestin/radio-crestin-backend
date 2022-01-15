const nextRuntimeDotenv = require('next-runtime-dotenv')

const withConfig = nextRuntimeDotenv({
    // path: '.env',
    public: [
    ],
    server: [
    ]
})


module.exports =withConfig({
})