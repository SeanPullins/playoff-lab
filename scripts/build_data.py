"""Reproducible, chronological NFL win-probability model. No future scores enter features."""
import csv,io,json,math,urllib.request,datetime,hashlib,pathlib,concurrent.futures
from zoneinfo import ZoneInfo
import numpy as np
from scipy.optimize import minimize
ROOT=pathlib.Path(__file__).resolve().parents[1]
URL='https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv'
ALIASES={'OAK':'LV','SD':'LAC','STL':'LAR','LA':'LAR','WAS':'WSH'}
def team(t):return ALIASES.get(t,t)
def read():
 raw=urllib.request.urlopen(URL,timeout=45).read(); rows=list(csv.DictReader(io.StringIO(raw.decode())))
 for r in rows:
  r['season']=int(r['season']);r['week']=int(r['week']);r['h']=team(r['home_team']);r['a']=team(r['away_team']);r['done']=bool(r['home_score']);r['hs']=float(r['home_score']) if r['done'] else 0;r['as_']=float(r['away_score']) if r['done'] else 0
 return raw,rows
TEAMS=['BUF','MIA','NE','NYJ','BAL','CIN','CLE','PIT','HOU','IND','JAX','TEN','DEN','KC','LAC','LV','DAL','NYG','PHI','WSH','CHI','DET','GB','MIN','ATL','CAR','NO','TB','ARI','LAR','SF','SEA']; ix={t:i for i,t in enumerate(TEAMS)}
def rating(games,prior,week):
 A=np.eye(32)*6.;b=np.array([prior.get(t,0)*6 for t in TEAMS],float)
 for g in games:
  h,a=ix[g['h']],ix[g['a']];weight=.97**max(0,week-g['week']);v=np.zeros(32);v[h]=1;v[a]=-1
  margin=np.clip(g['hs']-g['as_']-(0 if g['location']=='Neutral' else 2),-28,28)
  A+=weight*np.outer(v,v);b+=weight*margin*v
 r=np.linalg.solve(A,b);r-=r.mean();return dict(zip(TEAMS,r))
def feature(g,r):return [r[g['h']]-r[g['a']],0 if g['location']=='Neutral' else 1, max(-7,min(7,float(g.get('home_rest') or 7)-float(g.get('away_rest') or 7)))]
def baseline(g,past):
 def rate(t):
  gg=[x for x in past if t in (x['h'],x['a'])];w=sum(.5 if x['hs']==x['as_'] else float((x['hs']>x['as_'])==(x['h']==t)) for x in gg);return (w+2)/(len(gg)+4)
 h,a=rate(g['h']),rate(g['a']);return 1/(1+math.exp(-(math.log(h/(1-h))-math.log(a/(1-a))+.18)))
def metrics(pred):
 p=np.array([x[0] for x in pred]);y=np.array([x[1] for x in pred]);return {'games':len(p),'brier':round(float(np.mean((p-y)**2)),5),'logLoss':round(float(-np.mean(y*np.log(p)+(1-y)*np.log(1-p))),5),'accuracy':round(float(np.mean((p>=.5)==(y>=.5))),5)}
def main():
 raw,rows=read()
 def scoreboard(week):
  url=f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=2026&seasontype=2&week={week}&limit=1000'
  return json.load(urllib.request.urlopen(url,timeout=40))
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex: boards=list(ex.map(scoreboard,range(1,19)))
 live={}
 for board in boards:
  for e in board.get('events',[]):
   c=e['competitions'][0];h=next(x for x in c['competitors'] if x['homeAway']=='home');a=next(x for x in c['competitors'] if x['homeAway']=='away')
   live[e['id']]={'h':team(h['team']['abbreviation']),'a':team(a['team']['abbreviation']),'hs':int(h.get('score',0)),'as_':int(a.get('score',0)),'done':e['status']['type']['completed'],'date':e['date'],'neutral':bool(c.get('neutralSite',False)),'timeTBD':not c.get('timeValid',True)}
 assert len(live)==272,'Incomplete ESPN season; retain previous published snapshot'
 for g in rows:
  if g['season']==2026 and g['game_type']=='REG':
   e=live[g['espn']];assert (g['h'],g['a'])==(e['h'],e['a']),'Source matchup disagreement'
   g.update({k:e[k] for k in ['hs','as_','done','date','timeTBD']});g['location']='Neutral' if e['neutral'] else 'Home'
 regs=[r for r in rows if r['game_type']=='REG'];features=[];prior={};snapshots={}
 for year in range(2009,2027):
  season=[g for g in regs if g['season']==year];prior={t:.6*prior.get(t,0) for t in TEAMS};past=[]
  for week in sorted(set(g['week'] for g in season)):
   r=rating(past,prior,week)
   for g in season:
    if g['week']==week and g['done']:
     y=.5 if g['hs']==g['as_'] else float(g['hs']>g['as_']);features.append((year,feature(g,r),y,baseline(g,past)))
   past.extend(g for g in season if g['week']==week and g['done'])
  last=max((g['week'] for g in past),default=1);end=rating(past,prior,last)
  if year==2026:snapshots={'ratings':end,'season':season,'past':past}
  prior=end
 train=[x for x in features if 2010<=x[0]<=2021];X=np.array([x[1] for x in train]);y=np.array([x[2] for x in train])
 def loss(b):
  z=X@b;return np.mean(np.logaddexp(0,z)-y*z)+.001*np.sum(b*b)
 fit=minimize(loss,[.12,.20,.02],method='BFGS');beta=fit.x
 test=[x for x in features if 2023<=x[0]<=2025];pred=[(float(1/(1+np.exp(-np.dot(x[1],beta)))),x[2]) for x in test];old=[(x[3],x[2]) for x in test]
 # Paired season-bootstrap interval, descriptive with only three seasons.
 rng=np.random.default_rng(47);diff=np.array([(p[0]-p[1])**2-(b[0]-b[1])**2 for p,b in zip(pred,old)]);delta=[]
 for _ in range(2000):delta.append(float(np.mean(rng.choice(diff,len(diff),replace=True))))
 report={'modelVersion':'2.0.0','training':'2010–2021 regular seasons','test':'2023–2025 regular seasons; one chronological evaluation, no tuning on this test','method':'Opponent-adjusted point-margin ridge rating; previous-season ratings retain 60% of their prior value; 6-game ridge shrinkage; margins capped at 28; 0.97 weekly recency decay. Logistic coefficients fitted only on 2010–2021.','coefficients':beta.tolist(),'upgraded':metrics(pred),'original':metrics(old),'brierDifference95CI':np.quantile(delta,[.025,.975]).tolist(),'intervalNote':'Paired game bootstrap; games are correlated, so interval is descriptive and may be optimistic.','playoffCalibration':'Not backtested for playoff-event probabilities. Game-level results do not establish playoff-odds calibration.','source':URL,'sourceSha256':hashlib.sha256(raw).hexdigest()}
 current=snapshots['season'];games=[]
 for g in current:
  x=feature(g,snapshots['ratings']);p=float(1/(1+np.exp(-np.dot(x,beta))));games.append({'id':g.get('espn') or g['game_id'],'week':g['week'],'date':g['date'],'timeTBD':g.get('timeTBD',False),'h':g['h'],'a':g['a'],'hs':int(g['hs']),'as_':int(g['as_']),'done':g['done'],'neutral':g['location']=='Neutral','p':round(max(.02,min(.98,p)),6)})
 assert len(games)==272 and len(set(g['id'] for g in games))==272
 for t in TEAMS:assert sum(t in (g['h'],g['a']) for g in games)==17
 data={'season':2026,'updated':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'ESPN scoreboard (2026 schedule and results); nflverse (history and rest)','historySourceSha256':report['sourceSha256'],'sourceSha256':hashlib.sha256(raw+json.dumps(live,sort_keys=True).encode()).hexdigest(),'ratings':{t:round(float(r),3) for t,r in snapshots['ratings'].items()},'games':games,'model':report}
 (ROOT/'dist/data.json').write_text(json.dumps(data,separators=(',',':')));(ROOT/'dist/validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
