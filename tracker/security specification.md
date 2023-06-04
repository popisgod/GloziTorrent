# This File describes the security specifications of the tracker API 

## Token system 

The API system requires client login (currently only supports Admin Login)
The client receives an Oauth2 token and a refresh token. 
The tokens are bineded to the ip of the user and the use of them on a different system will force a user re-login. 

### Token expiration 
The Oauth2 token expires after a set amount of time, before which the user will refresh the token using the refresh token.
The refresh process creates a new pair of refresh and Oauth2 tokens, And any future use of the old refresh token will revoke the current refresh token too. 
this is taken a security measure against the stealing of the tokens.
Using the refersh token from a different IP will revoke the refresh token, and re-login will be necessary. 



## Rate limiting 


## Design Plan and Road Map
    
    - implementing the refresh token
    - adding better handling to security scopes  
    - limiting generation of tokens and refresh tokens 
    - implementing rate limits 

    