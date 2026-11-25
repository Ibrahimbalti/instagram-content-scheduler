#!/usr/bin/env python3
"""Direct Instagram publisher. No Composio, paid AI, scheduler SaaS, artifacts or caches.
Defaults to offline validation. Publishing requires explicit configuration and a secret.
"""
import argparse, base64, hashlib, json, os, re, sys, time, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
UTC=timezone.utc
class SafetyError(RuntimeError): pass
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None
OPENER=build_opener(NoRedirect())

def normalized(text):
    return unicodedata.normalize('NFC','\n'.join(s.rstrip() for s in (text or '').replace('\r\n','\n').split('\n')).strip())
def caption_hash(text): return hashlib.sha256(normalized(text).encode()).hexdigest()
def moment(text): return datetime.fromisoformat(text.replace('Z','+00:00'))
def validate(cfg,root=ROOT):
    if cfg.get('expected_repository')!='Ibrahimbalti/instagram-content-scheduler': raise SafetyError('Unexpected repository configuration.')
    if cfg.get('expected_instagram_username')!='md_ibrahim07_official': raise SafetyError('Unexpected Instagram destination.')
    posts=cfg['posts']; zone=ZoneInfo(cfg['timezone'])
    if len(posts)!=30: raise SafetyError('This batch must contain exactly 30 approved posts.')
    seen=set(); prev=None
    for i,p in enumerate(posts,1):
        dt=moment(p['publish_at']).astimezone(zone)
        if p['day']!=i or not dt.tzinfo: raise SafetyError('Invalid post order or timezone.')
        if prev and (dt.date()-prev).days!=1: raise SafetyError('Dates must be consecutive.')
        prev=dt.date()
        if dt.hour!=21 or dt.minute!=0: raise SafetyError('Unapproved target posting time.')
        h=caption_hash(p['caption'])
        if h in seen or len(p['caption'])>2200: raise SafetyError('Duplicate or oversized caption.')
        seen.add(h)
        n=len(p['media'])
        if (p['format']=='FEED_POST' and n!=1) or (p['format']=='CAROUSEL' and not 2<=n<=10): raise SafetyError('Invalid media count.')
        for m in p['media']:
            f=(root/m['path']).resolve()
            if not f.is_relative_to(root.resolve()) or not f.is_file(): raise SafetyError('Missing or unsafe asset path.')
            data=f.read_bytes()
            if not data.startswith(b'\xff\xd8') or len(data)>8*1024*1024: raise SafetyError('Unsupported image.')
            if hashlib.sha256(data).hexdigest()!=m['sha256']: raise SafetyError('An approved asset was changed.')
            if len(m['alt_text'])>1000: raise SafetyError('Alt text too long.')
    return posts

def due_post(cfg,now):
    local=now.astimezone(ZoneInfo(cfg['timezone']))
    for p in cfg['posts']:
        due=moment(p['publish_at'])
        if due.date()==local.date() and now>=due: return p
    return None

def authorized(cfg,env):
    if not cfg.get('enabled') or not cfg.get('content_approved'): raise SafetyError('Campaign is not approved and enabled.')
    if env.get('ENABLE_INSTAGRAM_PUBLISHING')!='true': raise SafetyError('Publishing activation variable is off.')
    if env.get('GITHUB_REPOSITORY','').lower()!=cfg['expected_repository'].lower(): raise SafetyError('Wrong repository or local publishing is not permitted.')
    if not env.get('INSTAGRAM_ACCESS_TOKEN') or not env.get('GH_TOKEN'): raise SafetyError('Required encrypted credentials are missing.')

def request_json(host,path,token,method='GET',params=None,body=None):
    if host not in ('https://api.github.com','https://graph.instagram.com'): raise SafetyError('Unapproved API host.')
    url=host+path
    if params: url+='?'+urlencode(params)
    headers={'Authorization':'Bearer '+token,'User-Agent':'Ibrahim-Instagram-Scheduler','Accept':'application/json'}
    if host=='https://api.github.com': headers['Accept']='application/vnd.github+json'
    data=None
    if body is not None:
        if host=='https://api.github.com': data=json.dumps(body).encode();headers['Content-Type']='application/json'
        else: data=urlencode(body).encode();headers['Content-Type']='application/x-www-form-urlencoded'
    attempts=3 if method=='GET' else 1  # Never blindly retry a publishing mutation.
    for attempt in range(attempts):
        try:
            with OPENER.open(Request(url,data=data,headers=headers,method=method),timeout=45) as response:
                raw=response.read()
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            # Never print the URL, request headers, token or raw provider response.
            if method=='GET' and exc.code in (429,500,502,503,504) and attempt<attempts-1:
                time.sleep(2**(attempt+1));continue
            raise SafetyError(f'{host.split("//")[1]} returned HTTP {exc.code}; stopped safely.') from None
        except (URLError,TimeoutError):
            if method=='GET' and attempt<attempts-1: time.sleep(2**(attempt+1));continue
            raise SafetyError('Network result is uncertain; stopped without retrying a write.') from None

class GitHub:
    def __init__(self,repo,token): self.repo=repo;self.token=token
    def call(self,path='',method='GET',body=None):
        return request_json('https://api.github.com','/repos/'+self.repo+path,self.token,method,body=body)
    def verify_public(self):
        info=self.call()
        if info.get('private') is not False or info.get('visibility')!='public': raise SafetyError('Only a public repository is allowed by the zero-charge configuration.')
    def load(self):
        f=self.call('/contents/state/ledger.json')
        self.sha=f['sha']
        return json.loads(base64.b64decode(f['content']))
    def save(self,state):
        value=base64.b64encode((json.dumps(state,indent=2,sort_keys=True)+'\n').encode()).decode()
        out=self.call('/contents/state/ledger.json','PUT',{'message':'Record Instagram publishing checkpoint','content':value,'sha':self.sha})
        self.sha=out['content']['sha']
    def disable(self):
        self.call('/actions/workflows/instagram.yml/disable','PUT')

class Instagram:
    def __init__(self,token,version):
        if not re.fullmatch(r'v\d+\.\d+',version): raise SafetyError('Invalid Graph API version.')
        self.token=token;self.prefix='/'+version;self.user=None
    def call(self,path,method='GET',params=None,body=None):
        return request_json('https://graph.instagram.com',self.prefix+path,self.token,method,params,body)
    def verify(self,expected):
        me=self.call('/me',params={'fields':'id,username'})
        if me.get('username','').lower()!=expected.lower(): raise SafetyError('Instagram token belongs to a different account.')
        self.user=me['id']
        self.call('/'+self.user+'/content_publishing_limit')
    def find_existing(self,post):
        # Read recent media before every write; do not infer that a timeout means failure.
        begin=moment(post['publish_at']).replace(hour=0,minute=0,second=0,microsecond=0)
        after=None;target=caption_hash(post['caption'])
        for _ in range(10):
            q={'fields':'id,caption,timestamp,permalink','limit':100,'since':int(begin.timestamp())}
            if after:q['after']=after
            out=self.call('/'+self.user+'/media',params=q)
            rows=out.get('data',[])
            if not isinstance(rows,list): raise SafetyError('Unexpected media response.')
            for row in rows:
                if row.get('timestamp') and moment(row['timestamp'])>=begin and caption_hash(row.get('caption',''))==target:
                    return {'media_id':row['id'],'permalink':row.get('permalink')}
            paging=out.get('paging',{})
            if not rows or not paging.get('next'): return None
            after=paging.get('cursors',{}).get('after')
            if not after: raise SafetyError('Unable to finish duplicate check safely.')
        raise SafetyError('Duplicate check exceeded safe pagination bound; publication blocked.')
    def ready(self,cid):
        for _ in range(40):
            out=self.call('/'+cid,params={'fields':'status_code'})
            status=out.get('status_code')
            if status=='FINISHED':return
            if status in ('ERROR','EXPIRED','PUBLISHED'): raise SafetyError('Container is not safely publishable: '+status)
            time.sleep(3)
        raise SafetyError('Container processing timed out; no publish request sent.')
    def container(self,post,repository,commit):
        urls=['https://raw.githubusercontent.com/'+repository+'/'+commit+'/'+quote(m['path'],safe='/') for m in post['media']]
        if post['format']=='FEED_POST':
            out=self.call('/'+self.user+'/media','POST',body={'image_url':urls[0],'caption':post['caption'],'alt_text':post['media'][0]['alt_text']})
            return out['id']
        children=[]
        for url,m in zip(urls,post['media']):
            out=self.call('/'+self.user+'/media','POST',body={'image_url':url,'is_carousel_item':'true','alt_text':m['alt_text']})
            self.ready(out['id']);children.append(out['id'])
        return self.call('/'+self.user+'/media','POST',body={'media_type':'CAROUSEL','children':','.join(children),'caption':post['caption']})['id']
    def publish(self,cid): return self.call('/'+self.user+'/media_publish','POST',body={'creation_id':cid})['id']

def publish_due(cfg,post,ig,journal,repository,commit):
    state=journal.load();entries=state.setdefault('entries',{});key=str(post['day']);h=caption_hash(post['caption'])
    entry=entries.get(key,{})
    if entry and entry.get('caption_sha256')!=h: raise SafetyError('Published/checkpointed copy was altered; manual review required.')
    if entry.get('status')=='published': return 'already_recorded'
    match=ig.find_existing(post)
    if match:
        entries[key]={'status':'published','caption_sha256':h,**match};journal.save(state)
        return 'reconciled'
    if entry.get('status') in ('publish_intent','uncertain'):
        raise SafetyError('Previous publish outcome is uncertain; no automatic duplicate attempt will be made.')
    cid=entry.get('container_id')
    if not cid:
        cid=ig.container(post,repository,commit)
        entries[key]={'status':'container_created','caption_sha256':h,'container_id':cid};journal.save(state)
    ig.ready(cid)
    entries[key]['status']='publish_intent';journal.save(state) # Must persist BEFORE the external publish.
    try:
        media_id=ig.publish(cid)
    except SafetyError:
        entries[key]['status']='uncertain';journal.save(state)
        raise
    entries[key].update(status='published',media_id=media_id)
    journal.save(state) # If this fails, the next run reconciles via caption before any publish.
    return 'published'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['check','preflight','publish'],default='check')
    parser.add_argument('--at',help='Offline schedule simulation only; not allowed with preflight/publish.')
    args=parser.parse_args()
    cfg=json.loads((ROOT/'campaign.json').read_text());posts=validate(cfg)
    if args.at and args.mode!='check': raise SafetyError('Time overrides are restricted to offline checks.')
    now=moment(args.at) if args.at else datetime.now(UTC)
    post=due_post(cfg,now)
    if args.mode=='check':
        print(json.dumps({'mode':'offline_check','posts':len(posts),'images':sum(len(p['media']) for p in posts),'enabled':cfg['enabled'],'content_approved':cfg['content_approved'],'due_day':post['day'] if post else None,'network_calls':0},indent=2));return
    repo=os.environ.get('GITHUB_REPOSITORY','')
    if repo.lower()!=cfg['expected_repository'].lower(): raise SafetyError('Wrong repository.')
    token=os.environ.get('INSTAGRAM_ACCESS_TOKEN','');ght=os.environ.get('GH_TOKEN','')
    if not token or not ght: raise SafetyError('Configure the encrypted token before the read-only preflight.')
    gh=GitHub(repo,ght);gh.verify_public()
    ig=Instagram(token,cfg['graph_api_version'])
    if args.mode=='preflight':
        ig.verify(cfg['expected_instagram_username'])
        print('Read-only preflight passed for the expected Instagram account and publishing-limit endpoint. No media was created or published. Token expiry and full 30-day validity still require verification at authorization.');return
    authorized(cfg,os.environ)
    last=moment(posts[-1]['publish_at']).astimezone(ZoneInfo(cfg['timezone'])).date()
    if now.astimezone(ZoneInfo(cfg['timezone'])).date()>last:
        gh.disable();print('Campaign window ended; workflow disabled without backfilling old posts.');return
    if not post: print('No approved post is due; no Instagram requests made.');return
    ig.verify(cfg['expected_instagram_username'])
    commit=os.environ.get('GITHUB_SHA','')
    if not re.fullmatch(r'[0-9a-fA-F]{40}',commit): raise SafetyError('Missing immutable content revision.')
    result=publish_due(cfg,post,ig,gh,repo,commit)
    print(json.dumps({'day':post['day'],'result':result,'instagram_username':cfg['expected_instagram_username']}))
    if post['day']==30 and result in ('published','already_recorded','reconciled'):
        gh.disable();print('Final post complete; future scheduled runs disabled.')

if __name__=='__main__':
    try:main()
    except SafetyError as exc:
        print('SAFE STOP: '+str(exc),file=sys.stderr);sys.exit(1)
