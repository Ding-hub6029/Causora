"""Real server-side providers. No fixtures, credentials or canned response fallback."""
from __future__ import annotations
import asyncio
import hashlib
import json
import math
import os
import threading
import time
from typing import Any
from .wire import PipelineConfig

class ProviderFailure(RuntimeError):
    def __init__(self,reason:str):super().__init__(reason);self.reason=reason


def family_of(model:str)->str:
    if model.startswith('gpt-'):return 'openai-gpt'
    if model.startswith('gemini-'):return 'google-gemini'
    return 'unknown'

class CallBudget:
    """A shared pre-request limit across providers; does not query account balances."""
    def __init__(self,limit:int):
        if not isinstance(limit,int) or not 1<=limit<=12:raise ValueError('Explicit finite provider request limit required')
        self.limit=limit;self.used=0;self._lock=asyncio.Lock()
    async def acquire(self):
        async with self._lock:
            if self.used>=self.limit:raise ProviderFailure('provider_call_budget_exhausted')
            self.used+=1

class LiveProvider:
    kind='LIVE_PROVIDER'
    supports_request_timeout=True

    def __init__(self,model:str,*,max_calls:int=12,timeout:float|None=None,budget:CallBudget|None=None,config:PipelineConfig|None=None):
        key=os.getenv('OPENAI_API_KEY');base=os.getenv('OPENAI_API_BASE') or os.getenv('OPENAI_BASE_URL')
        if not key or not base:raise ProviderFailure('provider_not_configured')
        if not model or family_of(model)=='unknown':raise ProviderFailure('provider_model_not_configured')
        self.config=config or PipelineConfig()
        # An unclassified SDK client must be safe for a Critic request. Every actual
        # request below receives its role-specific deadline through with_options.
        sdk_timeout=self._valid_timeout(self.config.critic_timeout if timeout is None else timeout,'SDK timeout')
        from openai import AsyncOpenAI
        self.client=AsyncOpenAI(api_key=key,base_url=base,max_retries=0,timeout=sdk_timeout)
        self.model=model;self.family=family_of(model);self.max_calls=max_calls;self.calls=0;self.audit=[]
        self._lock=asyncio.Lock()
        self.budget=budget or CallBudget(max_calls)
        self.sdk_timeout=sdk_timeout

    @staticmethod
    def _valid_timeout(value:float|int,description:str)->float:
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
            raise ValueError(description+' must be a finite positive number')
        return float(value)

    def _request_timeout(self,stage:str,request_timeout:float|None)->float:
        if request_timeout is not None:return self._valid_timeout(request_timeout,'request_timeout')
        configured=self.config.critic_timeout if stage.casefold()=='critic' else self.config.stage_timeout
        return self._valid_timeout(configured,'configured request timeout')

    async def complete(self,*,stage:str,payload:dict,schema:dict,system:str,request_timeout:float|None=None)->dict:
        effective_timeout=self._request_timeout(stage,request_timeout)
        async with self._lock:
            if self.calls>=self.max_calls:raise ProviderFailure('provider_call_budget_exhausted')
            await self.budget.acquire()
            self.calls+=1
        started=time.monotonic();body=json.dumps(payload,ensure_ascii=False,sort_keys=True,allow_nan=False)
        record={'stage':stage,'providerFamily':self.family,'model':self.model,'inputSha256':hashlib.sha256(body.encode()).hexdigest(),
            'source':'ACTUAL_PROVIDER_REQUEST','status':'started','sdkTimeoutSeconds':effective_timeout,
            'startedAtMonotonicSeconds':round(started,4)}
        self.audit.append(record)
        parameters={'model':self.model,'messages':[{'role':'system','content':system},{'role':'user','content':body}],
            'response_format':{'type':'json_schema','json_schema':{'name':'causora_'+stage.lower(),'strict':True,'schema':schema}}}
        if self.family=='google-gemini':
            parameters['max_tokens']=8192
            parameters['extra_body']={'thinking':{'budget_tokens':1024}}
        else:
            parameters['max_completion_tokens']=2000;parameters['extra_body']={'reasoning':{'effort':'minimal'}}
        try:
            response=await self.client.with_options(timeout=effective_timeout).chat.completions.create(**parameters)
            content=response.choices[0].message.content
            if not content:raise ProviderFailure('provider_empty_response')
            value=json.loads(content)
            if not isinstance(value,dict):raise ProviderFailure('provider_malformed_response')
            record['status']='returned';record['outputSha256']=hashlib.sha256(content.encode()).hexdigest()
            record['parsedOutput']=value
            if response.usage:record['usage']=response.usage.model_dump()
            return value
        except asyncio.CancelledError:
            record['status']='cancelled';raise
        except ProviderFailure as exc:record['status']=exc.reason;raise
        except Exception as exc:
            safe={'RateLimitError':'provider_rate_limited','APITimeoutError':'provider_timeout','AuthenticationError':'provider_authentication_failed',
                  'BadRequestError':'provider_bad_request','JSONDecodeError':'provider_malformed_response'}
            reason=safe.get(type(exc).__name__,'provider_unavailable');record['status']=reason
            raise ProviderFailure(reason) from None
        finally:record['elapsedSeconds']=round(time.monotonic()-started,4)

    async def aclose(self):await self.client.close()

class UnavailableCritic:
    kind='UNAVAILABLE_NOT_A_MODEL';model='not-configured';family='google-gemini'
    async def complete(self,**kwargs):raise ProviderFailure('gemini_not_configured')

def _factory_config_from_env()->PipelineConfig:
    """Parse and validate every pipeline timeout before any SDK client is created."""
    defaults=PipelineConfig()
    return PipelineConfig(
        total_timeout=float(os.getenv('CAUSORA_AI_TOTAL_TIMEOUT',str(defaults.total_timeout))),
        stage_timeout=float(os.getenv('CAUSORA_AI_STAGE_TIMEOUT',str(defaults.stage_timeout))),
        critic_timeout=float(os.getenv('CAUSORA_CRITIC_TIMEOUT',str(defaults.critic_timeout))),
        retries=int(os.getenv('CAUSORA_AI_RETRIES',str(defaults.retries))),
        max_calls=int(os.getenv('CAUSORA_AI_PIPELINE_CALLS',str(defaults.max_calls))),
    )


def _configured_model(name:str,default:str)->str:
    model=os.getenv(name,default).strip()
    if not model or family_of(model)=='unknown':raise ProviderFailure('provider_model_not_configured')
    return model


def _close_on_factory_failure(providers:list[LiveProvider])->None:
    """Close constructed SDK clients without hiding the configuration failure."""
    async def close_all():
        for provider in providers:
            try:await provider.aclose()
            except Exception:pass
    try:asyncio.get_running_loop()
    except RuntimeError:asyncio.run(close_all())
    else:
        # providers_from_env is synchronous. A short-lived loop in another thread
        # lets cleanup finish before re-raising even when the caller has an event loop.
        thread=threading.Thread(target=lambda:asyncio.run(close_all()),daemon=True)
        thread.start();thread.join()


def providers_from_env():
    """Construct configured live providers with one shared, capped request budget."""
    # Explicit OpenRouter mode is intentionally a separate transport.  In particular it
    # reads only OPENROUTER_API_KEY inside its module and cannot fall back to generic
    # OpenAI-compatible proxy credentials when that dedicated key is absent or preflight fails.
    if os.getenv('CAUSORA_AI_PROVIDER','').strip().casefold()=='openrouter':
        from .openrouter_provider import providers_from_openrouter_env
        return providers_from_openrouter_env()
    # This is deliberately first: malformed environment values must fail before an
    # AsyncOpenAI object (and therefore any SDK resource) is constructed.
    config=_factory_config_from_env()
    budget=CallBudget(int(os.getenv('CAUSORA_AI_MAX_CALLS','12')))
    primary_id=_configured_model('CAUSORA_PRIMARY_MODEL','gpt-5-mini')
    critic_id=os.getenv('CAUSORA_GEMINI_CRITIC_MODEL','').strip()
    if critic_id and family_of(critic_id)=='unknown':raise ProviderFailure('provider_model_not_configured')
    fallback_id=_configured_model('CAUSORA_FALLBACK_CRITIC_MODEL',primary_id)
    if family_of(fallback_id)!=family_of(primary_id):raise ProviderFailure('fallback_not_same_family')

    constructed=[]
    try:
        primary=LiveProvider(primary_id,max_calls=budget.limit,budget=budget,config=config,timeout=config.stage_timeout)
        constructed.append(primary)
        critic=(LiveProvider(critic_id,max_calls=4,budget=budget,config=config,timeout=config.critic_timeout)
                if critic_id else UnavailableCritic())
        if isinstance(critic,LiveProvider):constructed.append(critic)
        # Keep a distinct fallback client even when it uses the primary model ID:
        # fallback Critic requests must retain the Critic SDK default, not 10 seconds.
        fallback=LiveProvider(fallback_id,max_calls=4,budget=budget,config=config,timeout=config.critic_timeout)
        constructed.append(fallback)
        if fallback.family!=primary.family:raise ProviderFailure('fallback_not_same_family')
        return primary,critic,fallback,config
    except BaseException:
        _close_on_factory_failure(constructed)
        raise
