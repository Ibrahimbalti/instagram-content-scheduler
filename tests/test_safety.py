import unittest,json,copy,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import publisher as p
CFG=json.loads((p.ROOT/'campaign.json').read_text())
class Journal:
    def __init__(self,state=None): self.state=state or {'entries':{}};self.saved=0
    def load(self):return self.state
    def save(self,state):self.saved+=1;self.state=state
class IG:
    def __init__(self,existing=None,fail=False):self.existing=existing;self.fail=fail;self.published=0;self.created=0
    def find_existing(self,post):return self.existing
    def container(self,*args):self.created+=1;return 'container-1'
    def ready(self,cid):pass
    def publish(self,cid):
        self.published+=1
        if self.fail:raise p.SafetyError('simulated uncertain outcome')
        return 'media-1'
class SafetyTests(unittest.TestCase):
    def test_all_original_assets_and_captions_validate(self):self.assertEqual(len(p.validate(CFG)),30)
    def test_before_start_no_post(self):self.assertIsNone(p.due_post(CFG,datetime(2026,11,25,16,tzinfo=timezone.utc)))
    def test_target_time_not_early(self):self.assertIsNone(p.due_post(CFG,datetime(2026,11,26,15,59,tzinfo=timezone.utc)))
    def test_target_time(self):self.assertEqual(p.due_post(CFG,datetime(2026,11,26,16,tzinfo=timezone.utc))['day'],1)
    def test_no_old_post_backfill(self):self.assertEqual(p.due_post(CFG,datetime(2026,11,28,17,tzinfo=timezone.utc))['day'],3)
    def test_after_end_no_post(self):self.assertIsNone(p.due_post(CFG,datetime(2026,12,26,16,tzinfo=timezone.utc)))
    def test_disabled_by_default(self):
        with self.assertRaises(p.SafetyError):p.authorized(CFG,{})
    def test_changed_caption_stops(self):
        j=Journal({'entries':{'1':{'status':'published','caption_sha256':'not-the-approved-copy'}}})
        with self.assertRaises(p.SafetyError):p.publish_due(CFG,CFG['posts'][0],IG(),j,CFG['expected_repository'],'a'*40)
    def test_duplicate_reconciles_without_publish(self):
        ig=IG(existing={'media_id':'existing'});j=Journal()
        self.assertEqual(p.publish_due(CFG,CFG['posts'][0],ig,j,CFG['expected_repository'],'a'*40),'reconciled')
        self.assertEqual((ig.created,ig.published),(0,0))
    def test_uncertain_intent_blocks_duplicate(self):
        post=CFG['posts'][0];j=Journal({'entries':{'1':{'status':'publish_intent','caption_sha256':p.caption_hash(post['caption'])}}});ig=IG()
        with self.assertRaises(p.SafetyError):p.publish_due(CFG,post,ig,j,CFG['expected_repository'],'a'*40)
        self.assertEqual(ig.published,0)
    def test_success_then_repeat_does_not_republish(self):
        ig=IG();j=Journal();post=CFG['posts'][0]
        self.assertEqual(p.publish_due(CFG,post,ig,j,CFG['expected_repository'],'a'*40),'published')
        self.assertEqual(p.publish_due(CFG,post,ig,j,CFG['expected_repository'],'a'*40),'already_recorded')
        self.assertEqual(ig.published,1)
    def test_failed_publish_not_blindly_retried(self):
        ig=IG(fail=True);j=Journal();post=CFG['posts'][0]
        with self.assertRaises(p.SafetyError):p.publish_due(CFG,post,ig,j,CFG['expected_repository'],'a'*40)
        with self.assertRaises(p.SafetyError):p.publish_due(CFG,post,ig,j,CFG['expected_repository'],'a'*40)
        self.assertEqual(ig.published,1)
if __name__=='__main__':unittest.main()
