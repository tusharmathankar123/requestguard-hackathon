"""Loopback-only FastAPI surface. Reviewer labels are not authenticated identities."""
import os
from pathlib import Path
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict, Field

from requestguard import budget
from .agent import ProposalAgent, SCENARIOS
from .orchestrator import Orchestrator, Conflict


class Submission(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=2000)
    pause_before_execution: bool = Field(default=False,strict=True)


class Approval(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reviewer: str = Field(pattern=r'^[A-Za-z0-9_.-]{2,60}$')


def create_app(path='local-data/control-tower.sqlite', *, live=False, agent=None, contract=None):
    if live and (os.environ.get('REQUESTGUARD_LIVE_ENABLED')!='YES' or not os.environ.get('MODEL_API_KEY')):
        raise ValueError('Live mode requires explicit activation and a server-side Meta key')
    tower=Orchestrator(path,agent or ProposalAgent(os.environ['MODEL_API_KEY'] if live else None),contract)
    app=FastAPI(title='AgentGuard Control Tower',version='0.1.0')
    app.state.tower=tower
    token=secrets.token_urlsafe(32)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])

    @app.middleware('http')
    async def local_boundary(request: Request, call_next):
        if request.method not in ('GET','HEAD'):
            origin=request.headers.get('origin')
            if origin and origin!=str(request.base_url).rstrip('/'):
                return JSONResponse({'detail':'cross_origin_denied'},status_code=403)
            if request.headers.get('sec-fetch-site')=='cross-site' or not secrets.compare_digest(request.headers.get('x-tower-token',''),token):
                return JSONResponse({'detail':'local_session_token_required'},status_code=403)
            chunks=[]
            size=0
            async for chunk in request.stream():
                size+=len(chunk)
                if size>8192:
                    return JSONResponse({'detail':'request_too_large'},status_code=413)
                chunks.append(chunk)
            request._body=b''.join(chunks)
        return await call_next(request)

    @app.exception_handler(Conflict)
    async def conflict_handler(request,exc):
        return JSONResponse({'detail':str(exc)},status_code=409)

    @app.exception_handler(KeyError)
    async def missing_handler(request,exc):
        return JSONResponse({'detail':'workflow_not_found'},status_code=404)

    @app.get('/api/state')
    def state():
        allowance=None
        if tower.agent.mode=='meta':
            try:
                allowance=budget.status()
            except budget.LiveBudgetError:
                allowance={'available':False,'reason':'live_allowance_unavailable'}
        return {'mode':tower.agent.mode,'scenarios':SCENARIOS,'workflows':tower.list(),
                'ledger':tower.ledger(),'allowance':allowance,'session_token':token,
                'contract':{'agent':tower.contract.name,'tools':sorted(tower.contract.tools),'permissions':sorted(tower.contract.permissions)},
                'policy':{'automatic_through_eur':250,'approval_through_eur':500,'hard_limit_eur':500}}

    @app.post('/api/workflows')
    def create(payload:Submission):
        return tower.create(payload.text,payload.pause_before_execution)

    @app.post('/api/workflows/{wid}/approve')
    def approve(wid:str,payload:Approval):
        return tower.approve(wid,payload.reviewer)

    @app.post('/api/workflows/{wid}/recover')
    def recover(wid:str):
        return tower.recover(wid)

    dist=Path(__file__).resolve().parents[1]/'frontend'/'dist'
    if dist.exists():
        app.mount('/',StaticFiles(directory=dist,html=True),name='control-tower')
    else:
        @app.get('/')
        def build_needed():
            return JSONResponse({'detail':'Build frontend first: cd frontend && npm install && npm run build'},status_code=503)
    return app
