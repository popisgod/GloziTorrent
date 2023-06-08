import re
import logging
import uvicorn
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Annotated, List, Dict, Callable
from classy_fastapi import Routable, get, post
from pymongo import MongoClient
from starlette.authentication import requires
from starlette.authentication import AuthCredentials, AuthenticationError
from starlette.requests import HTTPConnection
from starlette.middleware.authentication import AuthenticationMiddleware


# logging configuration 
logging.basicConfig(filename='tracker.log', 
                    level=logging.INFO, 
                    filemode='w', 
                    format='%(asctime)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S')


class TrackerWEB(Routable):
    def __init__(self) -> None:
        super().__init__()

    
    @get('/')
    def get_root(self) -> HTMLResponse:
        return HTMLResponse(content=
            """
                <html>
                    <head>
                        <title>Root</title>
                    </head>
                    <body>
                        <h1>this is the root page</h1>
                    </body>
                </html>
            """,
            status_code=200)
    
    @get('/admin')
    @requires(scopes=['admin'])
    def get_admin_root(self, request : Request) -> HTMLResponse:
        return HTMLResponse(content=
            """
                <html>
                    <head>
                        <title>Root</title>
                    </head>
                    <body>
                        <h1>this is the root Admin page</h1>
                    </body>
                </html>
            """,
            status_code=200)