"""Command-contract tests only; no Docker builds or cloud access."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.log = self.directory / 'commands.jsonl'
        fake = self.directory / 'gcloud'
        fake.write_text('#!/usr/bin/env python3\nimport json,os,sys\nwith open(os.environ["COMMAND_LOG"],"a") as f:f.write(json.dumps(sys.argv[1:])+"\\n")\n')
        fake.chmod(0o755)
        self.api = {'GCP_PROJECT':'highground-test','GCP_REGION':'asia-southeast1','VERTEX_LOCATION':'asia-southeast1','GEMINI_FAST_MODEL':'configured-flash','GEMINI_PRO_MODEL':'configured-pro','GCS_BUCKET':'private-test','PUBSUB_TOPIC':'flood-events','BQ_DATASET':'highground','WEB_BASE_URL':'https://web.example.test','API_BASE_URL':'https://api.example.test','SCHEDULER_AUDIENCE':'https://api.example.test','SCHEDULER_CALLER_EMAIL':'scheduler@highground-test.iam.gserviceaccount.com','SCHEDULER_CALLER_SUBJECT':'12345','DEMO_MODE':'true'}
        self.api_path = self.directory / 'api.json'
        self.web_path = self.directory / 'web.json'
        self.web_path.write_text(json.dumps({'HIGHGROUND_API_ORIGIN':'https://api.example.test'}))
        self.env = {**os.environ,'PATH':str(self.directory)+os.pathsep+os.environ['PATH'],'COMMAND_LOG':str(self.log),'GCP_PROJECT':'highground-test','GCP_REGION':'asia-southeast1','API_SERVICE':'highground-api','WEB_SERVICE':'highground-web','API_SERVICE_ACCOUNT':'api@highground-test.iam.gserviceaccount.com','WEB_SERVICE_ACCOUNT':'web@highground-test.iam.gserviceaccount.com','API_ENV_FILE':str(self.api_path),'WEB_ENV_FILE':str(self.web_path)}
        self.env.pop('HOSTING_AUTHORIZED',None)
        for kind in ('API','WEB'):
            self.env[kind+'_IMAGE']='asia-southeast1-docker.pkg.dev/highground-test/images/'+kind.lower()+'@sha256:'+'a'*64
        for name in ('TELEGRAM_BOT_TOKEN','TELEGRAM_WEBHOOK_SECRET','HASH_SALT','DEMO_OPERATOR_TOKEN'):
            self.env[name+'_SECRET']=name.lower()+':1'

    def run_script(self, *args):
        self.api_path.write_text(json.dumps(self.api))
        return subprocess.run(['bash',str(ROOT/'infra/deploy.sh'),*args],env=self.env,capture_output=True,text=True,timeout=10)

    def test_default_dryrun_never_calls_cloud(self):
        result=self.run_script()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(self.log.exists())

    def test_execution_requires_hosting_authorization(self):
        self.assertNotEqual(self.run_script('--execute').returncode,0)
        self.assertFalse(self.log.exists())

    def test_explicit_execution_passes_fixed_target_and_secret_references(self):
        self.env['HOSTING_AUTHORIZED']='true'
        result=self.run_script('--execute')
        self.assertEqual(result.returncode,0,result.stderr)
        commands=[json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(len(commands),2)
        self.assertTrue(all('--project=highground-test' in c and '--port=8080' in c for c in commands))
        self.assertIn('--set-secrets=TELEGRAM_BOT_TOKEN=telegram_bot_token:1,TELEGRAM_WEBHOOK_SECRET=telegram_webhook_secret:1,HASH_SALT=hash_salt:1,DEMO_OPERATOR_TOKEN=demo_operator_token:1',commands[0])
        self.assertFalse(any('scheduler' in c or 'builds' in c for c in commands))

    def test_bad_targets_plaintext_secrets_and_hosted_bypass_fail_closed(self):
        for mutation in ('project','secret','bypass','origin'):
            with self.subTest(mutation=mutation):
                old_api=self.api.copy();old_env=self.env.copy()
                if mutation=='project':self.env['GCP_PROJECT']='dover-tts'
                if mutation=='secret':self.api['TELEGRAM_BOT_TOKEN']='private-value'
                if mutation=='bypass':self.api['SCHEDULER_LOCAL_AUTH']='true'
                if mutation=='origin':self.api['API_BASE_URL']='https://evil.test/path'
                result=self.run_script()
                self.assertNotEqual(result.returncode,0)
                self.assertNotIn('private-value',result.stdout+result.stderr)
                self.assertFalse(self.log.exists())
                self.api=old_api;self.env=old_env


if __name__=='__main__': unittest.main()
