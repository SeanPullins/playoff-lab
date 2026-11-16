import json,sys,pathlib,copy,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from community import validate,ingest
DATA={'games':[{'id':'browns-fixture','week':12,'h':'CLE','a':'LV','date':'2026-11-29T18:00:00Z','done':False},{'id':'other-fixture','week':11,'h':'HOU','a':'IND','date':'2026-11-19T18:00:00Z','done':False},{'id':'monday-fixture','week':10,'h':'BAL','a':'LAC','date':'2026-11-17T01:15:00Z','done':False}]}
GAME=DATA['games'][0]
def event(p,number=1,date='2026-11-16T12:00:00Z'):
 return {'action':'opened','issue':{'number':number,'created_at':date,'user':{'login':'test-fan'},'html_url':f'https://github.com/SeanPullins/playoff-lab/issues/{number}','title':'TEMU | Test fixture','body':'```json\n'+json.dumps({'version':1,**p})+'\n```'}}
class TestCommunity(unittest.TestCase):
 def test_pick_accepts_pre_kickoff(self):
  r=validate(event({'kind':'pickem','week':GAME['week'],'league':'friends','picks':{GAME['id']:1}}),DATA);self.assertEqual(r['picks'][GAME['id']],1)
 def test_late_pick_rejected(self):
  with self.assertRaises(ValueError):validate(event({'kind':'pickem','week':GAME['week'],'picks':{GAME['id']:1}},date='2027-02-01T12:00:00Z'),DATA)
 def test_cross_week_rejected(self):
  with self.assertRaises(ValueError):validate(event({'kind':'pickem','week':GAME['week']%18+1,'picks':{GAME['id']:1}}),DATA)
 def test_receipt_accepts_and_freezes(self):
  e=event({'kind':'receipt','week':GAME['week'],'game':GAME['id'],'winner':1,'note':'A genuine pregame call.'});r=ingest(e,DATA,{'entries':[]});e['issue']['body']=e['issue']['body'].replace('genuine','changed');r=ingest(e,DATA,r);self.assertEqual(len(r['entries']),1);self.assertIn('genuine',r['entries'][0]['note'])
 def test_edited_event_ignored(self):
  e=event({'kind':'confidence','week':10,'topic':'coaching','value':9});e['action']='edited';self.assertIsNone(validate(e,DATA))
 def test_confidence_bounds(self):
  for v in [0,11,True,'9']:
   with self.assertRaises(ValueError):validate(event({'kind':'confidence','week':10,'topic':'coaching','value':v}),DATA)
 def test_award_period_validated(self):
  self.assertEqual(validate(event({'kind':'award','week':10,'category':'mvp','period':'weekly','nominee':'A player'}),DATA)['period'],'weekly')
  with self.assertRaises(ValueError):validate(event({'kind':'award','week':10,'category':'mvp','period':'bogus','nominee':'A player'}),DATA)
 def test_shell_metacharacters_remain_literal(self):
  p={'kind':'receipt','week':GAME['week'],'game':GAME['id'],'winner':0,'note':'$(touch /tmp/never-run); <script>alert(1)</script>'};r=validate(event(p),DATA);self.assertEqual(r['note'],p['note'])
 def test_invalid_league_rejected(self):
  with self.assertRaises(ValueError):validate(event({'kind':'pickem','week':GAME['week'],'league':'../../bad','picks':{GAME['id']:1}}),DATA)
 def test_non_browns_receipt_rejected(self):
  g=next(g for g in DATA['games'] if not g['done'] and 'CLE' not in [g['h'],g['a']])
  with self.assertRaises(ValueError):validate(event({'kind':'receipt','week':g['week'],'game':g['id'],'winner':1}),DATA)
 def test_future_poll_rejected(self):
  with self.assertRaises(ValueError):validate(event({'kind':'confidence','week':18,'topic':'coaching','value':8}),DATA)
 def test_tbd_kickoff_rejected(self):
  d=copy.deepcopy(DATA);d['games'][0]['timeTBD']=True
  with self.assertRaises(ValueError):validate(event({'kind':'pickem','week':GAME['week'],'picks':{GAME['id']:1}}),d)
 def test_past_confidence_poll_rejected(self):
  with self.assertRaises(ValueError):validate(event({'kind':'confidence','week':9,'topic':'coaching','value':8}),DATA)
 def test_unrelated_issue_ignored(self):
  e=event({'kind':'confidence','week':10,'topic':'coaching','value':8});e['issue']['title']='A bug';self.assertIsNone(validate(e,DATA))
if __name__=='__main__':unittest.main()
