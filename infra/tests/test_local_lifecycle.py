"""Lifecycle command contracts; Docker mutations are replaced by a fake boundary."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
emulators=load('emulators');gate=load('local_gate')

def record(spec):
    return {'Id':'a'*64,'Name':'/'+spec.name,'Image':spec.image.split('@')[1],'Config':{'Image':spec.image,'Entrypoint':{'gcs':['/bin/fake-gcs-server','-data','/data'],'bigquery':['/bin/bigquery-emulator']}.get(spec.role),'Cmd':list(spec.command),'Env':list(spec.environment),'Labels':{'highground.project':'highground','highground.role':spec.role+'-emulator'}},'HostConfig':{'Memory':spec.memory,'MemorySwap':spec.swap,'Privileged':False,'NetworkMode':'bridge','PortBindings':{str(spec.port)+'/tcp':[{'HostIp':'127.0.0.1','HostPort':str(spec.port)}]}},'Mounts':[{'Type':'volume','Name':spec.volume,'Destination':'/data','RW':True}] if spec.volume else [],'State':{'Running':True}}

class LifecycleTests(unittest.TestCase):
    def test_ephemeral_stop_requires_explicit_disposable_ack_before_commands(self):
        spec=emulators.SPECS[0]
        with patch.object(emulators,'inspect',return_value=record(spec)),patch.object(emulators,'docker') as command:
            with self.assertRaises(ValueError):emulators.operate('stop',(spec,))
            command.assert_not_called()

    def test_stop_rechecks_identity_and_targets_exact_id_not_name(self):
        spec=emulators.SPECS[0];before=record(spec);after=copy.deepcopy(before);after['Id']='b'*64
        with patch.object(emulators,'inspect',side_effect=[before,after]),patch.object(emulators,'docker') as command:
            with self.assertRaises(ValueError):emulators.operate('stop',(spec,),ack=True)
            command.assert_not_called()
        with patch.object(emulators,'inspect',return_value=before),patch.object(emulators,'docker') as command:
            emulators.operate('stop',(spec,),ack=True)
            command.assert_called_once_with('stop','--time','20','a'*64)

    def test_foreign_image_port_mount_and_owner_refused(self):
        spec=emulators.SPECS[0]
        for field in ('image','port','mount','owner'):
            value=record(spec)
            if field=='image':value['Image']='sha256:foreign'
            if field=='port':value['HostConfig']['PortBindings']['8787/tcp'][0]['HostIp']='0.0.0.0'
            if field=='mount':value['Mounts']=[{'Type':'bind'}]
            if field=='owner':value['Config']['Labels']['highground.project']='unrelated'
            with self.subTest(field=field),patch.object(emulators,'inspect',return_value=value),patch.object(emulators,'docker') as command:
                with self.assertRaises(ValueError):emulators.operate('stop',(spec,),ack=True)
                command.assert_not_called()

    def test_start_refuses_legacy_unbounded_without_recreation(self):
        spec=emulators.SPECS[1];value=record(spec);value['HostConfig']['Memory']=0
        with patch.object(emulators,'inspect',return_value=value),patch.object(emulators,'docker') as command:
            with self.assertRaises(ValueError):emulators.operate('start',(spec,))
            command.assert_not_called()

    def test_creation_uses_pinned_loopback_bounded_spec_and_existing_bq_volume(self):
        for spec in emulators.SPECS:
            args=emulators.run_command(spec)
            self.assertIn(spec.image,args);self.assertIn(f'127.0.0.1:{spec.port}:{spec.port}',args)
            self.assertIn('--memory='+str(spec.memory),args)
            self.assertNotIn('--rm',args)
        spec=emulators.SPECS[-1]
        with patch.object(emulators,'inspect',return_value=None),patch.object(emulators,'docker') as command:
            emulators.operate('start',(spec,))
            self.assertEqual(command.call_args_list[0].args,('volume','inspect',emulators.VOLUME))
            self.assertEqual(command.call_count,2)

    def test_explicit_fresh_bigquery_initialization_is_scoped_and_refuses_retained_data(self):
        spec=emulators.SPECS[-1]
        with patch.object(emulators,'inspect',return_value=None),patch.object(emulators,'docker',return_value='') as command:
            emulators.operate('start',(spec,),initialize=True)
            calls=[call.args for call in command.call_args_list]
            self.assertIn(('volume','create','--label','highground.project=highground','--label','highground.role=bigquery-data',emulators.VOLUME),calls)
        for specs in [emulators.SPECS,(emulators.SPECS[0],)]:
            with self.assertRaises(ValueError):emulators.operate('start',specs,initialize=True)
        with patch.object(emulators,'inspect',return_value=record(spec)),patch.object(emulators,'docker') as command:
            with self.assertRaises(ValueError):emulators.operate('start',(spec,),initialize=True)
            command.assert_not_called()
        with patch.object(emulators,'inspect',return_value=None),patch.object(emulators,'docker',return_value='retained-data') as command:
            with self.assertRaises(ValueError):emulators.operate('start',(spec,),initialize=True)
            self.assertFalse(any(call.args[0:2]==('volume','create') for call in command.call_args_list))

    def test_fresh_initialization_refuses_orphaned_recovered_volume(self):
        spec=emulators.SPECS[-1]
        def boundary(*args):
            if args==('volume','ls','--filter','name=^highground-bigquery-recovered-data$','--format','{{.Name}}'):
                return 'highground-bigquery-recovered-data\n'
            return ''
        with patch.object(emulators,'inspect',return_value=None),patch.object(emulators,'docker',side_effect=boundary) as command:
            with self.assertRaisesRegex(ValueError,'Retained BigQuery data'):
                emulators.operate('start',(spec,),initialize=True)
            self.assertFalse(any(call.args[:2]==('volume','create') or call.args[0]=='run' for call in command.call_args_list))

    def test_environment_defaults_never_accept_cloud_and_unit_blocks_dotenv_reload(self):
        self.assertEqual(gate.environment('full',{},gate.ENDPOINTS),gate.ENDPOINTS)
        bad={**gate.ENDPOINTS,'STORAGE_EMULATOR_HOST':'https://storage.googleapis.com'}
        with self.assertRaises(ValueError):gate.environment('full',bad,gate.ENDPOINTS)
        with self.assertRaises(ValueError):gate.environment('full',{}, {})
        self.assertTrue(all(gate.environment('unit',bad,gate.ENDPOINTS)[name]=='' for name in gate.ENDPOINTS))

    def test_full_gate_rejects_any_actual_junit_skip(self):
        with tempfile.TemporaryDirectory() as directory:
            report=Path(directory)/'result.xml';report.write_text('<testsuites><testsuite><testcase><skipped message="emulator absent"/></testcase></testsuite></testsuites>')
            with self.assertRaises(ValueError):gate.require_no_skips(report)
            report.write_text('<testsuites><testsuite><testcase/></testsuite></testsuites>');gate.require_no_skips(report)

if __name__=='__main__':unittest.main()
