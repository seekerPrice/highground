"""Intercepted CLI contracts only: these tests never provision Google Cloud."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAKE = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ['COMMAND_LOG'], 'a') as f: f.write(json.dumps([Path(sys.argv[0]).name, *args])+'\\n')
s = ' '.join(args)
mode = os.environ.get('TEST_MODE','existing')
if mode == 'permission' and 'firestore databases describe' in s:
 print('PERMISSION_DENIED',file=sys.stderr);sys.exit(1)
if mode == 'missing' and (' describe ' in ' '+s+' ' or ' show ' in ' '+s+' ') and not s.startswith('projects ') and not s.startswith('billing '):
 print('NOT_FOUND',file=sys.stderr);sys.exit(1)
if 'value(projectNumber)' in s: print('123456');sys.exit()
if 'value(projectId)' in s: print('highground-test');sys.exit()
if 'value(billingEnabled)' in s: print('True');sys.exit()
if 'firestore databases describe' in s:
 print(json.dumps({'type':'FIRESTORE_NATIVE','locationId':'us-central1' if mode=='conflict' else 'asia-southeast1'}))
elif 'storage buckets describe' in s:
 print(json.dumps({'name':'highground-media-highground-test','location':'ASIA-SOUTHEAST1','projectNumber':'999999' if mode=='bucket-owner' else '123456','iamConfiguration':{'uniformBucketLevelAccess':{'enabled':True},'publicAccessPrevention':'enforced'}}))
elif 'secrets describe' in s:
 print(json.dumps({'replication':{'userManaged':{'replicas':[{'location':'asia-southeast1'}]}}}))
elif 'iam service-accounts describe' in s:
 print(json.dumps({'email':'highground-api@highground-test.iam.gserviceaccount.com','disabled':False}))
elif 'iam roles describe' in s:
 print(json.dumps({'includedPermissions':['bigquery.tables.get','bigquery.tables.updateData']}))
elif ' show ' in ' '+s+' ':
 ident=args[-1]
 if '.' in ident:
  schema=json.loads((Path(os.environ['SCHEMA_DIR'])/(ident.split('.')[-1]+'.json')).read_text())
  print(json.dumps({'type':'TABLE','schema':{'fields':schema}}))
 else: print(json.dumps({'location':'asia-southeast1'}))
else: print('{}')
'''


class SetupContract(unittest.TestCase):
    def run_setup(self, mode: str = 'existing', project: str | None = 'highground-test'):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            for tool in ('gcloud', 'bq'):
                fake = path / tool
                fake.write_text(FAKE)
                fake.chmod(0o755)
            log = path / 'commands.jsonl'
            env = {**os.environ, 'PATH': f'{path}:{os.environ["PATH"]}',
                   'PYTHONOPTIMIZE': '1', 'COMMAND_LOG': str(log), 'SCHEMA_DIR': str(ROOT / 'schemas'), 'TEST_MODE': mode}
            env.pop('GCP_PROJECT', None)
            env.pop('GCP_REGION', None)
            if project is not None:
                env['GCP_PROJECT'] = project
            result = subprocess.run(['bash', str(ROOT / 'setup.sh'), '--apply'], env=env,
                                    capture_output=True, text=True)
            commands = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            return result, commands

    def test_missing_project_never_invokes_cloud(self):
        result, commands = self.run_setup(project=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands, [])

    def test_existing_resources_are_reused_and_commands_scoped(self):
        result, commands = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        for tool, *args in commands:
            self.assertIn('--project=highground-test' if tool == 'gcloud' else '--project_id=highground-test', args)
        self.assertFalse(any('create' in args for _, *args in commands))
        self.assertFalse(any('mk' in args for _, *args in commands))
        self.assertFalse(any('versions' in args or 'keys' in args for _, *args in commands))
        bindings = [args for tool, *args in commands if tool == 'bq' and 'add-iam-policy-binding' in args]
        self.assertEqual(len(bindings), 5)
        self.assertTrue(all('--table=true' in args for args in bindings))

    def test_absent_resources_created_without_secret_values(self):
        result, commands = self.run_setup('missing')
        self.assertEqual(result.returncode, 0, result.stderr)
        text = json.dumps(commands)
        self.assertIn('--uniform-bucket-level-access', text)
        self.assertIn('--public-access-prevention', text)
        self.assertIn('--type=firestore-native', text)
        self.assertEqual(sum('mk' in args for _, *args in commands), 6)
        self.assertEqual(sum('secrets' in args and 'create' in args for _, *args in commands), 2)
        self.assertNotIn('versions', text)

    def test_conflicting_region_stops_before_dependent_resources(self):
        result, commands = self.run_setup('conflict')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any('storage' in args for _, *args in commands))

    def test_bucket_owned_by_other_project_is_rejected(self):
        result, commands = self.run_setup('bucket-owner')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any('pubsub' in args for _, *args in commands))

    def test_permission_error_does_not_create_missing_resource(self):
        result, commands = self.run_setup('permission')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PERMISSION_DENIED', result.stderr)
        self.assertFalse(any('create' in args for _, *args in commands))


if __name__ == '__main__':
    unittest.main()
