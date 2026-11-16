"""Treat issue text as untrusted JSON, never as commands. Freeze first opened event."""
import json,re,datetime,pathlib,os,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
def utc(value):return datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
def validate(event,data,now=None):
 issue=event.get('issue',{});body=issue.get('body') or ''
 if event.get('action')!='opened' or not issue.get('title','').startswith('TEMU | '):return None
 if len(body)>14000:raise ValueError('Submission too large')
 match=re.search(r'```json\s*([\s\S]*?)\s*```',body)
 if not match:raise ValueError('Missing JSON submission')
 p=json.loads(match.group(1));kind=p.get('kind');when=utc(issue['created_at']);games={g['id']:g for g in data['games']}
 login=issue['user']['login']
 if not re.fullmatch(r'[A-Za-z0-9-]{1,39}',login):raise ValueError('Invalid GitHub login')
 r={'id':int(issue['number']),'user':login,'created':issue['created_at'],'kind':kind,'url':issue['html_url']}
 if p.get('version')!=1:raise ValueError('Unsupported submission version')
 week=p.get('week')
 if type(week)!=int or not 1<=week<=18:raise ValueError('Invalid week')
 r['week']=week
 if kind=='pickem':
  league=p.get('league','dawg-pound')
  if not re.fullmatch(r'[a-z0-9-]{1,40}',league):raise ValueError('League must be 1–40 lowercase letters, numbers or hyphens')
  picks=p.get('picks')
  if not isinstance(picks,dict) or not 1<=len(picks)<=16:raise ValueError('Choose 1–16 games')
  clean={}
  for gid,v in picks.items():
   if gid not in games or games[gid]['week']!=week or type(v) not in (int,float) or v not in (0,.5,1):raise ValueError('Invalid pick')
   if games[gid].get('timeTBD'):raise ValueError('Kickoff not confirmed; submission is not open yet')
   if when>=utc(games[gid]['date']):raise ValueError('A chosen game has already kicked off')
   clean[gid]=v
  r.update(league=league,picks=clean)
 elif kind=='confidence':
  maxweek=min([g['week'] for g in games.values() if utc(g['date'])>when]+[18])
  if week!=maxweek:raise ValueError('Only the current weekly confidence poll is open')
  topic=p.get('topic');value=p.get('value')
  if topic not in ['next-game','quarterback','coaching','playoffs'] or type(value)!=int or not 1<=value<=10:raise ValueError('Invalid confidence vote')
  r.update(topic=topic,value=value)
 elif kind=='award':
  maxweek=min([g['week'] for g in games.values() if utc(g['date'])>when]+[18])
  if week>maxweek:raise ValueError('Future weekly awards are not open')
  period=p.get('period','season')
  if period not in ['season','weekly']:raise ValueError('Invalid award period')
  r['period']=period
  category=p.get('category');nominee=p.get('nominee','').strip()
  if category not in ['mvp','play','surprise','unsung'] or not 1<=len(nominee)<=90:raise ValueError('Invalid award vote')
  if any(ord(c)<32 for c in nominee):raise ValueError('Invalid nominee')
  r.update(category=category,nominee=nominee)
 elif kind=='receipt':
  gid=p.get('game');v=p.get('winner');note=p.get('note','').strip()
  if gid not in games or games[gid]['week']!=week or 'CLE' not in [games[gid]['h'],games[gid]['a']]:raise ValueError('Choose a Browns game')
  if type(v) not in (int,float) or v not in (0,.5,1):raise ValueError('Invalid winner')
  if games[gid].get('timeTBD'):raise ValueError('Kickoff not confirmed; receipt submission is not open yet')
  if when>=utc(games[gid]['date']):raise ValueError('Receipts must be submitted before kickoff')
  if len(note)>240 or any(ord(c)<32 and c not in '\n\t' for c in note):raise ValueError('Invalid note')
  r.update(game=gid,winner=v,note=note)
 else:raise ValueError('Unknown submission kind')
 return r

def ingest(event,data,existing):
 r=validate(event,data)
 if r and not any(x['id']==r['id'] for x in existing['entries']):existing['entries'].append(r)
 existing['updated']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 return existing
if __name__=='__main__':
 data=json.loads((ROOT/'dist/data.json').read_text());path=ROOT/'dist/community.json';existing=json.loads(path.read_text())
 event=json.loads(pathlib.Path(os.environ['GITHUB_EVENT_PATH']).read_text())
 try:
  try:result=ingest(event,data,existing)
  except (ValueError,KeyError,TypeError,json.JSONDecodeError):
   print('Opened submission rejected; processing other pending entries')
   result=existing
  # GitHub concurrency keeps only the latest pending run. Recover unchanged,
  # unprocessed opened issues so a burst of submissions is not silently lost.
  known={r['id'] for r in result['entries']}
  repo=os.environ.get('GITHUB_REPOSITORY','SeanPullins/playoff-lab')
  for page in range(1,101):
   req=urllib.request.Request(f'https://api.github.com/repos/{repo}/issues?state=all&per_page=100&page={page}',headers={'Accept':'application/vnd.github+json','Authorization':'Bearer '+os.environ['GH_TOKEN']})
   batch=json.load(urllib.request.urlopen(req,timeout=30))
   for issue in batch:
    if issue.get('pull_request') or issue['number'] in known or issue.get('updated_at')!=issue.get('created_at'):continue
    try:
     r=validate({'action':'opened','issue':issue},data)
     if r:result['entries'].append(r);known.add(r['id'])
    except (ValueError,KeyError,TypeError,json.JSONDecodeError):pass
   if len(batch)<100:break
  path.write_text(json.dumps(result,indent=2));print('Community submissions processed')
 except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e:raise SystemExit('Submission rejected: '+str(e))
