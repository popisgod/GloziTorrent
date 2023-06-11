import config from '.config';
import * as moment from 'moment';


class FastAPIclient {
    constructor(overrides){
        this.config = { 
            ...config,
            ...overrides,
        }

        this.authToken = config.authToken
        this.login = this.login.bind(this)
        this.apiClient = this.getApClient(this.config)

    }

    login(username, password) {
        delete this.apiClient.defaults.headers['Authorization']

        const form_data = new  FormData()
        const grant_type = 'password';
        const item = {grant_type, username, password};
        for (const key in item) {
            form_data.append(key, item[key])

        }


        return this.apiClient.post('/login', form_data)
            .then((resp) => {
                localStorage.setItem('token', JSON.stringify(resp.data))
                return this.fetchUser();
            }
            )



    }

    fetchUser() {
        return this.apiClient.get('/admin').then(({data}) => {
          localStorage.setItem('user', JSON.stringify(data));
          return data;
        });
      }


    logout() {
        // Add here any other data that needs to be deleted from local storage
        // on logout
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      }

    getApiClient(config) {
        const initialConfig = {
          baseURL: `${config.apiBasePath}/api/`,
        };
        const client = axios.create(initialConfig);
        client.interceptors.request.use(localStorageTokenInterceptor);
        return client;
      }
    

}


function localStorageTokenInterceptor(config) {
    const headers = {};
    const tokenString = localStorage.getItem('token');
  
    if (tokenString) {
      const token = JSON.parse(tokenString);
      const decodedAccessToken = jwtDecode(token.access_token);
      const isAccessTokenValid =
              moment.unix(decodedAccessToken.exp).toDate() > new Date();
      if (isAccessTokenValid) {
        headers['Authorization'] = `Bearer ${token.access_token}`;
      } else {
        alert('Your login session has expired');
      }
    }
    config['headers'] = headers;
    return config;
  }
  

export default FastAPIClient;