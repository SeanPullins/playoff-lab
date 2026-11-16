"""Bundle actual ESPN roster and team statistics for the Browns hub."""
import urllib.request,json,pathlib,datetime,concurrent.futures,math
root=pathlib.Path(__file__).resolve().parents[1];out=root/'dist/hub-data.json'
previous=json.loads(out.read_text()) if out.exists() else {'players':[],'statistics':{}}
url='https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/cle/roster?season=2026'
def request(u):return json.load(urllib.request.urlopen(u,timeout=30))
try:
 raw=request(url);players=[]
 for group in raw.get('athletes',[]):
  for a in group.get('items',[]):players.append({'id':a['id'],'name':a.get('displayName') or a['fullName'],'position':a.get('position',{}).get('abbreviation',''),'jersey':a.get('jersey','')})
 if not players:raise ValueError('Empty roster')
 previous.update(updated=datetime.datetime.now(datetime.timezone.utc).isoformat(),source=url,players=players)
except Exception:
 if not previous['players']:raise
 print('Roster refresh unavailable; retaining previous roster')

def stat_team(team):
 slug={'WSH':'wsh','LAR':'lar'}.get(team,team.lower());url=f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{slug}/statistics?season=2026'
 try:
  raw=request(url)
  if raw.get('season',{}).get('year')!=2026:raise ValueError('Wrong season')
  cats={c['name']:{s['name']:s.get('value') for s in c['stats']} for c in raw['results']['stats']['categories']}
  def val(cat,name):
   v=cats.get(cat,{}).get(name)
   return float(v) if isinstance(v,(int,float)) and math.isfinite(v) else None
  def pergame(cat,name):
   a,b=val(cat,name),val(cat,'teamGamesPlayed');return a/b if a is not None and b else None
  return team,{'source':url,'checked':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passingYPG':val('passing','netPassingYardsPerGame'),'rushingYPG':val('rushing','rushingYardsPerGame'),'yardsPerRush':val('rushing','yardsPerRushAttempt'),'sacksForPG':pergame('defensive','sacks'),'sacksAllowedPG':pergame('passing','sacks'),'thirdDownPct':val('miscellaneous','thirdDownConvPct'),'turnoverDiff':val('miscellaneous','turnOverDifferential')}
 except Exception:return team,None
teams=list(json.loads((root/'dist/data.json').read_text())['ratings']);statistics=previous.get('statistics',{})
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 for team,result in ex.map(stat_team,teams):
  if result:statistics[team]=result
previous['statistics']=statistics;out.write_text(json.dumps(previous,indent=2));print('Hub data:',len(previous['players']),'players;',len(statistics),'teams with statistics')
