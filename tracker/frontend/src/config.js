import runtimeEnv from '@mars/heroku-js-runtime-env';

const env = runtimeEnv();
const config = {
  apiBasePath: env.REACT_APP_API_BASE_PATH || 'http://10.100.102.3:5000',
  reactAppMode: process.env.REACT_APP_MODE || 'dev',
};

export default config;